#!/usr/bin/env python3
"""
本地调试清洗脚本
从本地 Excel 文件读取数据进行清洗，不连接 Google Sheets
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.alias_utils import AliasMapper
from scripts.cleaning_rules import CleaningRules
from scripts.validators import DataValidator


class LocalCleaningPipeline:
    """本地清洗管线（用于调试）"""
    
    # 目标输出字段顺序
    OUTPUT_SCHEMA = [
        'service_date', 'service_week', 'service_slot',
        'sermon_title', 'series', 'scripture',
        'preacher_id', 'preacher_name',
        'catechism', 'reading',
        'worship_lead_id', 'worship_lead_name',
        'worship_team_ids', 'worship_team_names',
        'pianist_id', 'pianist_name',
        'songs',
        'audio_id', 'audio_name',
        'video_id', 'video_name',
        'propresenter_play_id', 'propresenter_play_name',
        'propresenter_update_id', 'propresenter_update_name',
        'assistant_id', 'assistant_name',
        'notes', 'source_row', 'updated_at'
    ]
    
    def __init__(self, config_path: str, alias_csv: str = None):
        """
        初始化本地清洗管线
        
        Args:
            config_path: 配置文件路径
            alias_csv: 别名 CSV 文件路径（可选）
        """
        self.config = self._load_config(config_path)
        self.alias_mapper = AliasMapper()
        self.cleaning_rules = CleaningRules(self.config['cleaning_rules'])
        self.validator = DataValidator(self.config)
        
        # 加载别名映射
        if alias_csv and Path(alias_csv).exists():
            self.alias_mapper.load_from_csv(alias_csv)
            stats = self.alias_mapper.get_stats()
            print(f"✅ 加载别名: {stats['total_aliases']} 个别名, {stats['unique_persons']} 个人员")
        else:
            print("⚠️  未加载别名映射，将使用默认 ID 生成")
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def read_excel(self, excel_path: str) -> pd.DataFrame:
        """读取 Excel 文件"""
        print(f"📖 读取 Excel: {excel_path}")
        df = pd.read_excel(excel_path)
        print(f"✅ 读取 {len(df)} 行, {len(df.columns)} 列")
        return df
    
    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """映射列名（从中文到英文）"""
        column_mapping = self.config['columns']
        reverse_mapping = {v: k for k, v in column_mapping.items()}
        df = df.rename(columns=reverse_mapping)
        return df
    
    def clean_data(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """清洗数据"""
        print("\n🧹 开始数据清洗...")
        
        # 1. 列名映射
        df = self._map_columns(raw_df)
        
        # 2. 应用清洗规则
        cleaned_rows = []
        for idx, row in df.iterrows():
            try:
                cleaned_row = self._clean_row(row, idx)
                cleaned_rows.append(cleaned_row)
            except Exception as e:
                print(f"⚠️  第 {idx + 2} 行清洗失败: {e}")
                cleaned_row = self._clean_row(row, idx, allow_errors=True)
                cleaned_row['notes'] = f"清洗错误: {str(e)}"
                cleaned_rows.append(cleaned_row)
        
        # 3. 构建输出 DataFrame
        clean_df = pd.DataFrame(cleaned_rows)
        
        # 4. 确保输出字段顺序
        clean_df = self._ensure_schema(clean_df)
        
        print(f"✅ 清洗完成: {len(clean_df)} 行")
        return clean_df
    
    def _clean_row(self, row: pd.Series, idx: int, allow_errors: bool = False) -> dict:
        """清洗单行数据"""
        cleaned = {}
        
        # 基础字段
        cleaned['source_row'] = idx + 2
        
        # 日期
        service_date = self.cleaning_rules.clean_date(row.get('service_date'))
        cleaned['service_date'] = service_date or ''
        
        # 服务周和时段
        cleaned['service_week'] = self.cleaning_rules.get_service_week(service_date) if service_date else None
        cleaned['service_slot'] = self.cleaning_rules.infer_service_slot()
        
        # 讲道信息
        cleaned['sermon_title'] = self.cleaning_rules.clean_text(row.get('sermon_title'))
        cleaned['series'] = self.cleaning_rules.clean_text(row.get('series'))
        cleaned['scripture'] = self.cleaning_rules.clean_scripture(row.get('scripture'))
        
        # 要理问答和读经
        cleaned['catechism'] = self.cleaning_rules.clean_text(row.get('catechism'))
        cleaned['reading'] = self.cleaning_rules.clean_text(row.get('reading'))
        
        # 讲员
        preacher_name = self.cleaning_rules.clean_name(row.get('preacher'))
        preacher_id, preacher_display = self.alias_mapper.resolve(preacher_name)
        cleaned['preacher_id'] = preacher_id
        cleaned['preacher_name'] = preacher_display
        
        # 敬拜带领
        worship_lead_name = self.cleaning_rules.clean_name(row.get('worship_lead'))
        worship_lead_id, worship_lead_display = self.alias_mapper.resolve(worship_lead_name)
        cleaned['worship_lead_id'] = worship_lead_id
        cleaned['worship_lead_name'] = worship_lead_display
        
        # 敬拜同工
        worship_team_names = self.cleaning_rules.merge_columns(row, ['worship_team_1', 'worship_team_2'])
        worship_team_ids, worship_team_displays = self.alias_mapper.resolve_list(worship_team_names)
        cleaned['worship_team_ids'] = json.dumps(worship_team_ids, ensure_ascii=False) if worship_team_ids else ''
        cleaned['worship_team_names'] = json.dumps(worship_team_displays, ensure_ascii=False) if worship_team_displays else ''
        
        # 司琴
        pianist_name = self.cleaning_rules.clean_name(row.get('pianist'))
        pianist_id, pianist_display = self.alias_mapper.resolve(pianist_name)
        cleaned['pianist_id'] = pianist_id
        cleaned['pianist_name'] = pianist_display
        
        # 歌曲
        songs_list = self.cleaning_rules.split_songs(row.get('songs'))
        cleaned['songs'] = json.dumps(songs_list, ensure_ascii=False) if songs_list else ''
        
        # 音控
        audio_name = self.cleaning_rules.clean_name(row.get('audio'))
        audio_id, audio_display = self.alias_mapper.resolve(audio_name)
        cleaned['audio_id'] = audio_id
        cleaned['audio_name'] = audio_display
        
        # 导播/摄影
        video_name = self.cleaning_rules.clean_name(row.get('video'))
        video_id, video_display = self.alias_mapper.resolve(video_name)
        cleaned['video_id'] = video_id
        cleaned['video_name'] = video_display
        
        # ProPresenter 播放
        pp_play_name = self.cleaning_rules.clean_name(row.get('propresenter_play'))
        pp_play_id, pp_play_display = self.alias_mapper.resolve(pp_play_name)
        cleaned['propresenter_play_id'] = pp_play_id
        cleaned['propresenter_play_name'] = pp_play_display
        
        # ProPresenter 更新
        pp_update_name = self.cleaning_rules.clean_name(row.get('propresenter_update'))
        pp_update_id, pp_update_display = self.alias_mapper.resolve(pp_update_name)
        cleaned['propresenter_update_id'] = pp_update_id
        cleaned['propresenter_update_name'] = pp_update_display
        
        # 助教
        assistant_name = self.cleaning_rules.clean_name(row.get('assistant'))
        assistant_id, assistant_display = self.alias_mapper.resolve(assistant_name)
        cleaned['assistant_id'] = assistant_id
        cleaned['assistant_name'] = assistant_display
        
        # 备注
        cleaned['notes'] = self.cleaning_rules.clean_text(row.get('notes', ''))
        
        # 时间戳
        cleaned['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        
        return cleaned
    
    def _ensure_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """确保 DataFrame 符合输出 Schema"""
        for col in self.OUTPUT_SCHEMA:
            if col not in df.columns:
                df[col] = ''
        df = df[self.OUTPUT_SCHEMA]
        return df
    
    def validate_data(self, df: pd.DataFrame):
        """校验数据"""
        print("\n✅ 开始数据校验...")
        report = self.validator.validate_dataframe(df)
        return report
    
    def save_output(self, df: pd.DataFrame, csv_path: str, json_path: str = None):
        """保存输出"""
        print(f"\n💾 保存输出...")
        
        # 保存 CSV
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"  ✅ CSV: {csv_path}")
        
        # 保存 JSON
        if json_path:
            df.to_json(json_path, orient='records', force_ascii=False, indent=2)
            print(f"  ✅ JSON: {json_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='本地调试清洗脚本（从 Excel 读取）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基本用法
  python scripts/debug_clean_local.py --excel tests/data.xlsx
  
  # 使用别名 CSV
  python scripts/debug_clean_local.py --excel tests/data.xlsx --aliases tests/aliases.csv
  
  # 指定输出路径
  python scripts/debug_clean_local.py --excel tests/data.xlsx -o tests/output.csv
        """
    )
    
    parser.add_argument(
        '--excel',
        type=str,
        required=True,
        help='Excel 文件路径'
    )
    parser.add_argument(
        '--aliases',
        type=str,
        default='tests/generated_aliases.csv',
        help='别名 CSV 文件路径'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.json',
        help='配置文件路径'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='tests/debug_clean_output.csv',
        help='输出 CSV 文件路径'
    )
    parser.add_argument(
        '--json',
        type=str,
        default='tests/debug_clean_output.json',
        help='输出 JSON 文件路径（可选）'
    )
    
    args = parser.parse_args()
    
    # 检查文件
    if not Path(args.excel).exists():
        print(f"❌ Excel 文件不存在: {args.excel}")
        sys.exit(1)
    
    if not Path(args.config).exists():
        print(f"❌ 配置文件不存在: {args.config}")
        sys.exit(1)
    
    print("=" * 60)
    print("🔧 本地调试清洗脚本")
    print("=" * 60)
    print()
    
    # 创建管线
    pipeline = LocalCleaningPipeline(args.config, args.aliases)
    
    # 读取数据
    raw_df = pipeline.read_excel(args.excel)
    
    # 清洗数据
    clean_df = pipeline.clean_data(raw_df)
    
    # 校验数据
    report = pipeline.validate_data(clean_df)
    
    # 保存输出
    pipeline.save_output(clean_df, args.output, args.json)
    
    # 打印摘要
    print("\n" + "=" * 60)
    print(report.format_report(max_issues=10))
    print("=" * 60)
    
    print("\n🎉 调试完成！")
    print(f"\n📊 输出文件:")
    print(f"  - {args.output}")
    if args.json:
        print(f"  - {args.json}")
    print()
    
    return 0 if report.error_rows == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

