#!/usr/bin/env python3
"""
变化检测模块
用于检测原始数据是否发生变化，支持增量更新
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


class ChangeDetector:
    """数据变化检测器"""
    
    def __init__(self, state_file: str = 'logs/pipeline_state.json'):
        """
        初始化变化检测器
        
        Args:
            state_file: 状态文件路径，用于存储上次运行的状态
        """
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """加载上次运行的状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载状态文件失败: {e}，将使用默认状态")
        
        return {
            'last_run': None,
            'last_hash': None,
            'last_row_count': 0,
            'last_update_time': None,
            'run_count': 0
        }
    
    def _save_state(self) -> None:
        """保存当前状态"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            logger.debug(f"状态已保存到 {self.state_file}")
        except Exception as e:
            logger.error(f"保存状态文件失败: {e}")
    
    def compute_hash(self, df: pd.DataFrame) -> str:
        """
        计算 DataFrame 的哈希值
        
        Args:
            df: 要计算哈希的 DataFrame
            
        Returns:
            哈希字符串
        """
        # 将 DataFrame 转换为 JSON 字符串（确保列顺序一致）
        df_sorted = df.sort_index(axis=1)  # 按列名排序
        json_str = df_sorted.to_json(orient='records', force_ascii=False, date_format='iso')
        
        # 计算 SHA-256 哈希
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    def has_changed(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        检查数据是否发生变化
        
        Args:
            df: 当前的 DataFrame
            
        Returns:
            (是否变化, 变化详情)
        """
        current_hash = self.compute_hash(df)
        current_row_count = len(df)
        
        last_hash = self.state.get('last_hash')
        last_row_count = self.state.get('last_row_count', 0)
        
        # 如果是首次运行
        if last_hash is None:
            return True, {
                'reason': 'first_run',
                'message': '首次运行，需要进行完整清洗',
                'current_rows': current_row_count,
                'previous_rows': 0,
                'row_change': current_row_count
            }
        
        # 如果哈希值相同，说明数据没有变化
        if current_hash == last_hash:
            return False, {
                'reason': 'no_change',
                'message': '数据未发生变化',
                'current_rows': current_row_count,
                'previous_rows': last_row_count,
                'row_change': 0
            }
        
        # 数据发生了变化
        row_change = current_row_count - last_row_count
        
        if row_change > 0:
            reason = 'rows_added'
            message = f'检测到新增 {row_change} 行数据'
        elif row_change < 0:
            reason = 'rows_removed'
            message = f'检测到删除 {abs(row_change)} 行数据'
        else:
            reason = 'rows_modified'
            message = '检测到数据内容变化'
        
        return True, {
            'reason': reason,
            'message': message,
            'current_rows': current_row_count,
            'previous_rows': last_row_count,
            'row_change': row_change
        }
    
    def update_state(self, df: pd.DataFrame, success: bool = True) -> None:
        """
        更新状态
        
        Args:
            df: 当前处理的 DataFrame
            success: 是否成功处理
        """
        if success:
            self.state['last_hash'] = self.compute_hash(df)
            self.state['last_row_count'] = len(df)
            self.state['last_update_time'] = datetime.utcnow().isoformat() + 'Z'
        
        self.state['last_run'] = datetime.utcnow().isoformat() + 'Z'
        self.state['run_count'] = self.state.get('run_count', 0) + 1
        
        self._save_state()
    
    def get_state_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        return {
            'last_run': self.state.get('last_run'),
            'last_update_time': self.state.get('last_update_time'),
            'last_row_count': self.state.get('last_row_count', 0),
            'run_count': self.state.get('run_count', 0),
            'has_previous_run': self.state.get('last_hash') is not None
        }
    
    def reset_state(self) -> None:
        """重置状态（用于强制更新）"""
        logger.info("重置状态，下次运行将执行完整清洗")
        self.state = {
            'last_run': None,
            'last_hash': None,
            'last_row_count': 0,
            'last_update_time': None,
            'run_count': 0
        }
        self._save_state()


def main():
    """测试变化检测功能"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from core.gsheet_utils import GSheetClient
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='测试数据变化检测')
    parser.add_argument('--config', default='config/config.json', help='配置文件路径')
    parser.add_argument('--reset', action='store_true', help='重置状态')
    args = parser.parse_args()
    
    # 加载配置
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 初始化检测器
    detector = ChangeDetector()
    
    if args.reset:
        detector.reset_state()
        print("✓ 状态已重置")
        return
    
    # 读取数据
    gsheet_client = GSheetClient()
    source_config = config['source_sheet']
    
    print(f"读取数据: {source_config['range']}")
    df = gsheet_client.read_range(source_config['url'], source_config['range'])
    print(f"✓ 读取 {len(df)} 行数据")
    
    # 检测变化
    has_changed, details = detector.has_changed(df)
    
    print(f"\n变化检测结果:")
    print(f"  是否变化: {'是' if has_changed else '否'}")
    print(f"  原因: {details['reason']}")
    print(f"  说明: {details['message']}")
    print(f"  当前行数: {details['current_rows']}")
    print(f"  上次行数: {details['previous_rows']}")
    
    # 显示状态摘要
    summary = detector.get_state_summary()
    print(f"\n状态摘要:")
    print(f"  上次运行: {summary['last_run'] or '从未运行'}")
    print(f"  上次更新: {summary['last_update_time'] or '从未更新'}")
    print(f"  运行次数: {summary['run_count']}")
    
    # 如果需要更新，可以调用 detector.update_state(df)


if __name__ == '__main__':
    main()

