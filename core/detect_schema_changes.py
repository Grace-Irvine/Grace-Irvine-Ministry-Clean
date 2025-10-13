#!/usr/bin/env python3
"""
Schema 变化检测工具
读取 source sheet 并检测未配置的新列，生成配置建议
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gsheet_utils import GSheetClient
from core.schema_manager import SchemaManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SchemaChangeDetector:
    """Schema 变化检测器"""
    
    def __init__(self, config_path: str):
        """
        初始化检测器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.gsheet_client = GSheetClient()
        self.schema_manager = SchemaManager(self.config)
    
    def detect_changes(self) -> Dict[str, Any]:
        """
        检测 schema 变化
        
        Returns:
            检测报告
        """
        logger.info("开始检测 schema 变化...")
        
        # 读取 source sheet
        source_config = self.config['source_sheet']
        has_departments = 'departments' in self.config and self.config['departments']
        
        if has_departments:
            df, department_map = self.gsheet_client.read_range(
                source_config['url'],
                source_config['range'],
                return_department_info=True
            )
            logger.info(f"检测到部门信息: {len(department_map)} 列有部门标注")
        else:
            df = self.gsheet_client.read_range(
                source_config['url'],
                source_config['range']
            )
            department_map = {}
        
        source_columns = df.columns.tolist()
        logger.info(f"源表共有 {len(source_columns)} 列")
        
        # 检测新列
        new_columns = self.schema_manager.detect_new_columns(source_columns)
        
        # 映射现有列
        mapped, unmapped = self.schema_manager.map_source_columns(source_columns)
        
        # 生成报告
        report = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'source_sheet': source_config['url'],
            'total_columns': len(source_columns),
            'mapped_columns': len(mapped),
            'unmapped_columns': len(unmapped),
            'new_columns_detected': len(new_columns),
            'department_info_available': has_departments,
            'columns': {
                'all': source_columns,
                'mapped': mapped,
                'unmapped': unmapped,
                'new': new_columns
            }
        }
        
        # 如果有部门信息，添加到报告中
        if department_map:
            report['department_mapping'] = department_map
        
        # 生成配置建议
        if new_columns:
            logger.info(f"发现 {len(new_columns)} 个未配置的列")
            suggestions = self.schema_manager.generate_config_suggestions(
                new_columns,
                department_map
            )
            report['suggestions'] = suggestions
        else:
            logger.info("未发现新列，所有列均已配置")
            report['suggestions'] = None
        
        return report
    
    def save_report(self, report: Dict[str, Any], output_path: str) -> None:
        """
        保存报告到文件
        
        Args:
            report: 检测报告
            output_path: 输出文件路径
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"报告已保存到: {output_file}")
    
    def print_summary(self, report: Dict[str, Any]) -> None:
        """
        打印摘要
        
        Args:
            report: 检测报告
        """
        print("\n" + "=" * 70)
        print("Schema 变化检测报告")
        print("=" * 70)
        print(f"总列数: {report['total_columns']}")
        print(f"已配置列: {report['mapped_columns']}")
        print(f"未配置列: {report['unmapped_columns']}")
        print(f"新增列: {report['new_columns_detected']}")
        print(f"部门信息: {'可用' if report['department_info_available'] else '不可用'}")
        
        if report['new_columns_detected'] > 0:
            print("\n未配置的列:")
            for col in report['columns']['new']:
                dept = report.get('department_mapping', {}).get(col, '未知')
                print(f"  - {col} (部门: {dept})")
            
            print("\n配置建议已生成，请查看完整报告文件")
            print("建议的配置格式:")
            print("---")
            
            # 打印一个示例
            if report['suggestions'] and report['suggestions']['columns']:
                first_col = list(report['suggestions']['columns'].keys())[0]
                suggestion = report['suggestions']['columns'][first_col]
                print(f"简单格式: {suggestion['config_example_simple']}")
                print(f"高级格式: {json.dumps(suggestion['config_example_advanced'], ensure_ascii=False, indent=2)}")
        else:
            print("\n✅ 所有列均已配置，无需更新")
        
        print("=" * 70 + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='检测 Google Sheet schema 变化并生成配置建议'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.json',
        help='配置文件路径'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='logs/schema_detection_report.json',
        help='输出报告文件路径'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='安静模式（不打印摘要）'
    )
    
    args = parser.parse_args()
    
    try:
        # 创建检测器
        detector = SchemaChangeDetector(args.config)
        
        # 检测变化
        report = detector.detect_changes()
        
        # 保存报告
        detector.save_report(report, args.output)
        
        # 打印摘要
        if not args.quiet:
            detector.print_summary(report)
        
        # 返回退出码
        if report['new_columns_detected'] > 0:
            logger.warning("发现未配置的列，请更新配置文件")
            return 1
        else:
            logger.info("Schema 检测完成，所有列均已配置")
            return 0
    
    except Exception as e:
        logger.error(f"Schema 检测失败: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    import pandas as pd  # Import here for timestamp
    sys.exit(main())

