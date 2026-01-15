#!/usr/bin/env python3
"""
数据清洗管线主脚本
从原始 Google Sheet 读取、清洗、校验并写入清洗层 Google Sheet
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
from tqdm import tqdm

# 添加脚本目录到 Python 路径
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir.parent))

from core.gsheet_utils import GSheetClient
from core.alias_utils import AliasMapper
from core.cleaning_rules import CleaningRules
from core.validators import DataValidator
from core.service_layer import ServiceLayerManager
from core.schema_manager import SchemaManager


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CleaningPipeline:
    """数据清洗管线"""
    
    BASE_FIELDS = {
        'service_date',
        'series',
        'sermon_title',
        'scripture',
        'catechism',
        'songs',
        'notes',
    }
    
    def __init__(self, config_path: str):
        """
        初始化清洗管线
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.gsheet_client = GSheetClient()
        self.alias_mapper = AliasMapper()
        self.cleaning_rules = CleaningRules(self.config['cleaning_rules'])
        self.validator = DataValidator(self.config)
        self.schema_manager = SchemaManager(self.config)
        
        # 存储部门映射信息
        self.department_map = {}
        self.field_department_map = {}
        
        # 动态角色字段与输出 Schema
        self.role_fields = self._build_role_fields()
        self.output_schema = self._build_output_schema()
        
        # 加载别名映射
        self._load_aliases()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_aliases(self) -> None:
        """加载人名别名映射"""
        alias_config = self.config.get('alias_sources', {}).get('people_alias_sheet')
        
        if not alias_config:
            logger.warning("未配置人名别名数据源，将使用默认 ID 生成")
            return
        
        try:
            self.alias_mapper.load_from_sheet(
                self.gsheet_client,
                alias_config['url'],
                alias_config['range']
            )
            stats = self.alias_mapper.get_stats()
            logger.info(
                f"成功加载别名映射: {stats['total_aliases']} 个别名, "
                f"{stats['unique_persons']} 个唯一人员"
            )
        except Exception as e:
            logger.warning(f"加载别名映射失败: {e}，将使用默认 ID 生成")

    def _build_role_fields(self) -> List[str]:
        """
        从配置中构建角色字段列表（按配置顺序）
        """
        role_fields = []
        for field_name in self.schema_manager.column_configs.keys():
            if field_name.startswith('_'):
                continue
            if field_name in self.BASE_FIELDS:
                continue
            role_fields.append(field_name)
        return role_fields

    def _build_output_schema(self) -> List[str]:
        """
        根据配置动态生成输出字段顺序
        """
        schema: List[str] = []
        
        # 先放服务日期及衍生字段
        if 'service_date' in self.schema_manager.column_configs:
            schema.extend(['service_date', 'service_week', 'service_slot'])
        
        for field_name in self.schema_manager.column_configs.keys():
            if field_name.startswith('_'):
                continue
            if field_name == 'service_date':
                continue
            
            if field_name in self.BASE_FIELDS:
                schema.append(field_name)
                continue
            
            schema.extend([
                f"{field_name}_id",
                f"{field_name}_name",
                f"{field_name}_department"
            ])
        
        # 追加运行时字段
        for col in ['notes', 'source_row', 'updated_at']:
            if col not in schema:
                schema.append(col)
        
        return schema
    
    def read_source_data(self) -> pd.DataFrame:
        """读取原始数据"""
        source_config = self.config['source_sheet']
        logger.info(f"读取原始数据: {source_config['range']}")
        
        # 检查是否需要获取部门信息
        has_departments = 'departments' in self.config and self.config['departments']
        
        if has_departments:
            df, self.department_map = self.gsheet_client.read_range(
                source_config['url'],
                source_config['range'],
                return_department_info=True
            )
            logger.info(f"检测到部门信息: {len(self.department_map)} 列有部门标注")
            
            # 构建标准字段名到部门的映射
            self.field_department_map = {}
            for source_col, dept in self.department_map.items():
                field_name = self.schema_manager.get_standard_field_name(source_col)
                if field_name and dept:
                    self.field_department_map[field_name] = dept
        else:
            df = self.gsheet_client.read_range(
                source_config['url'],
                source_config['range']
            )
        
        logger.info(f"成功读取 {len(df)} 行原始数据")
        
        # 检测新列
        new_columns = self.schema_manager.detect_new_columns(df.columns.tolist())
        if new_columns:
            logger.warning(f"检测到 {len(new_columns)} 个未配置的列: {', '.join(new_columns)}")
            
            # 生成配置建议
            suggestions = self.schema_manager.generate_config_suggestions(
                new_columns, 
                self.department_map
            )
            
            # 保存到日志目录
            suggestion_file = Path('logs/schema_suggestions.json')
            suggestion_file.parent.mkdir(exist_ok=True)
            with open(suggestion_file, 'w', encoding='utf-8') as f:
                json.dump(suggestions, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置建议已保存到: {suggestion_file}")
        
        return df
    
    def clean_data(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗数据
        
        Args:
            raw_df: 原始 DataFrame
            
        Returns:
            清洗后的 DataFrame
        """
        logger.info("开始数据清洗...")
        
        # 1. 列名映射
        df = self._map_columns(raw_df)
        
        # 1.5 处理重复列（合并）
        df = self._merge_duplicate_columns(df)
        
        # 2. 应用清洗规则
        cleaned_rows = []
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="清洗数据"):
            try:
                cleaned_row = self._clean_row(row, idx)
                cleaned_rows.append(cleaned_row)
            except Exception as e:
                logger.error(f"清洗第 {idx + 2} 行时出错: {e}")
                # 仍然添加部分清洗的行，但标记错误
                cleaned_row = self._clean_row(row, idx, allow_errors=True)
                cleaned_row['notes'] = f"清洗错误: {str(e)}"
                cleaned_rows.append(cleaned_row)
        
        # 3. 构建输出 DataFrame
        clean_df = pd.DataFrame(cleaned_rows)
        
        # 4. 确保输出字段顺序
        clean_df = self._ensure_schema(clean_df)
        
        logger.info(f"数据清洗完成，共 {len(clean_df)} 行")
        
        # 5. 自动同步别名（如果启用）
        if self.config.get('alias_sources', {}).get('auto_sync', False):
            self._sync_aliases(clean_df)
        
        return clean_df
    
    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """映射列名（从中文到英文标准名）"""
        # 使用 SchemaManager 构建反向映射
        reverse_mapping = {}
        
        for field_name, mapping in self.schema_manager.field_to_mapping_map.items():
            # 将每个源列名映射到标准字段名
            for source_col in mapping.sources:
                reverse_mapping[source_col] = field_name
        
        # 重命名存在的列
        df = df.rename(columns=reverse_mapping)
        
        return df

    def _merge_duplicate_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        合并重复的列名（优先取非空值）
        """
        if not df.columns.duplicated().any():
            return df
            
        logger.info("发现重复列名，开始合并...")
        unique_cols = df.columns.unique()
        
        new_data = {}
        
        for col in unique_cols:
            col_data = df[col]
            if isinstance(col_data, pd.DataFrame):
                logger.info(f"合并重复列: {col}")
                # 将空字符串替换为 None
                temp = col_data.copy()
                # 使用 regex 替换空字符串或空白字符为 None
                temp = temp.replace(r'^\s*$', None, regex=True)
                
                # 使用 bfill(axis=1) 填充
                combined = temp.bfill(axis=1).iloc[:, 0]
                
                # 填充回空字符串
                combined = combined.fillna('')
                new_data[col] = combined
            else:
                new_data[col] = col_data
                
        return pd.DataFrame(new_data)
    
    def _clean_row(
        self, 
        row: pd.Series, 
        idx: int, 
        allow_errors: bool = False
    ) -> Dict[str, Any]:
        """
        清洗单行数据
        
        Args:
            row: 原始行
            idx: 行索引
            allow_errors: 是否允许错误（用于错误恢复）
            
        Returns:
            清洗后的行字典
        """
        cleaned = {}
        
        # 基础字段
        cleaned['source_row'] = idx + 2  # +2 因为索引从0开始且有表头
        
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
        
        # 要理问答
        cleaned['catechism'] = self.cleaning_rules.clean_text(row.get('catechism'))
        
        # 歌曲（拆分为列表）
        songs_list = self.cleaning_rules.split_songs(row.get('songs'))
        cleaned['songs'] = json.dumps(songs_list, ensure_ascii=False) if songs_list else ''
        
        # 角色字段（带别名映射）
        for role_field in self.role_fields:
            role_name = self.cleaning_rules.clean_name(row.get(role_field))
            role_id, role_display = self.alias_mapper.resolve(role_name)
            cleaned[f"{role_field}_id"] = role_id
            cleaned[f"{role_field}_name"] = role_display
            dept = self.schema_manager.get_department(role_field) or self.field_department_map.get(role_field, '')
            cleaned[f"{role_field}_department"] = dept
        
        # 备注
        cleaned['notes'] = self.cleaning_rules.clean_text(row.get('notes', ''))
        
        # 时间戳
        cleaned['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        
        return cleaned
    
    def _ensure_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """确保 DataFrame 符合输出 Schema"""
        # 添加缺失的列
        for col in self.output_schema:
            if col not in df.columns:
                df[col] = ''
        
        # 按指定顺序重排列
        df = df[self.output_schema]
        
        return df
    
    def _sync_aliases(self, clean_df: pd.DataFrame) -> None:
        """
        自动同步别名到 Google Sheets
        
        Args:
            clean_df: 清洗后的 DataFrame
        """
        try:
            logger.info("=" * 60)
            logger.info("开始自动同步别名...")
            
            # 获取配置
            alias_config = self.config.get('alias_sources', {})
            sheet_config = alias_config.get('people_alias_sheet', {})
            
            if not sheet_config:
                logger.warning("未配置 people_alias_sheet，跳过别名同步")
                return
            
            # 获取角色字段列表
            role_fields = alias_config.get('role_fields')
            if role_fields:
                role_fields = list(dict.fromkeys(role_fields + self.role_fields))
            else:
                role_fields = self.role_fields
            
            # 1. 从清洗后的数据中提取所有人名及其出现次数
            names_counter = self.alias_mapper.extract_names_from_cleaned_data(
                clean_df, 
                role_fields
            )
            
            if not names_counter:
                logger.info("未找到任何人名，跳过同步")
                return
            
            # 2. 同步到 Google Sheets
            url = sheet_config['url']
            range_name = sheet_config['range']
            
            stats = self.alias_mapper.sync_to_sheet(
                self.gsheet_client,
                url,
                range_name,
                names_counter
            )
            
            # 3. 输出统计信息
            logger.info("=" * 60)
            logger.info("✅ 别名同步完成！")
            logger.info(f"   📊 新增: {stats['new_added']} 个名字")
            logger.info(f"   📊 更新: {stats['updated']} 个名字的统计")
            logger.info(f"   📊 总计: {len(names_counter)} 个唯一人名")
            logger.info("=" * 60)
            
            if stats['new_added'] > 0:
                logger.info("💡 提示: 请在 Google Sheets 中检查新增的名字")
                logger.info("   1. 合并同一人的不同写法（修改 person_id）")
                logger.info("   2. 设置统一的 display_name")
                logger.info(f"   3. 表格链接: {url}")
                logger.info("=" * 60)
        
        except Exception as e:
            logger.warning(f"别名同步失败: {e}", exc_info=True)
            logger.warning("注意：别名同步失败不影响数据清洗流程")
    
    def validate_data(self, df: pd.DataFrame):
        """校验数据"""
        logger.info("开始数据校验...")
        report = self.validator.validate_dataframe(df)
        return report
    
    def write_output(self, df: pd.DataFrame, dry_run: bool = False) -> None:
        """
        写入输出
        
        Args:
            df: 清洗后的 DataFrame
            dry_run: 是否为干跑模式（仅输出预览，不写回 Sheet）
        """
        output_options = self.config['output_options']
        
        # 输出 CSV 预览
        if output_options.get('emit_csv_preview'):
            csv_path = output_options['emit_csv_preview']
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"已生成 CSV 预览: {csv_path}")
        
        # 输出 JSON 预览
        if output_options.get('emit_json_preview'):
            json_path = output_options['emit_json_preview']
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            df.to_json(json_path, orient='records', force_ascii=False, indent=2)
            logger.info(f"已生成 JSON 预览: {json_path}")
        
        # 写回 Google Sheet
        if not dry_run:
            target_config = self.config['target_sheet']
            logger.info(f"写入清洗层 Google Sheet: {target_config['range']}")
            
            result = self.gsheet_client.write_range(
                target_config['url'],
                target_config['range'],
                df,
                include_header=True
            )
            
            logger.info(
                f"成功写入 {result.get('updatedRows', 0)} 行数据到清洗层"
            )
        else:
            logger.info("干跑模式：跳过写入 Google Sheet")
    
    def generate_service_layer(self, df: pd.DataFrame) -> Dict[str, Dict[str, Path]]:
        """
        生成服务层数据（包括所有年份）
        
        Args:
            df: 清洗后的 DataFrame
            
        Returns:
            按年份保存的文件路径字典
        """
        service_layer_config = self.config.get('service_layer', {})
        
        if not service_layer_config.get('enabled', False):
            logger.info("服务层未启用，跳过")
            return {}
        
        logger.info("开始生成服务层数据（所有年份）...")
        
        # 初始化服务层管理器（传入 alias_mapper 以确保 generated json 使用最新别名）
        manager = ServiceLayerManager(self.alias_mapper)
        
        # 获取配置
        domains = service_layer_config.get('domains', ['sermon', 'volunteer', 'worship'])
        output_dir = Path(service_layer_config.get('local_output_dir', 'logs/service_layer'))
        
        # 生成所有年份的数据
        saved_files = manager.generate_all_years(df, output_dir, domains)
        
        # 如果配置了 Cloud Storage，上传到 bucket
        storage_config = service_layer_config.get('storage', {})
        if storage_config.get('provider') == 'gcs' and storage_config.get('bucket'):
            try:
                from core.cloud_storage_utils import DomainStorageManager
                
                bucket_name = storage_config['bucket']
                base_path = storage_config.get('base_path', 'domains/')
                service_account_file = storage_config.get('service_account_file')
                
                logger.info(f"上传服务层数据到 Cloud Storage: gs://{bucket_name}/{base_path}")
                
                storage_manager = DomainStorageManager(
                    bucket_name=bucket_name,
                    service_account_file=service_account_file,
                    base_path=base_path
                )
                
                # 上传所有年份的数据
                for year, year_files in saved_files.items():
                    logger.info(f"上传 {year} 数据...")
                    for domain, file_path in year_files.items():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            domain_data = json.load(f)
                        
                        # 根据是否为 latest 决定上传路径
                        if year == 'latest':
                            # 直接上传 latest 数据，强制上传为 latest.json（避免自动提取年份）
                            uploaded = storage_manager.upload_domain_data(domain, domain_data, sync_latest=False, force_latest=True)
                        else:
                            # 上传年份文件，不立即同步（避免重复同步）
                            uploaded = storage_manager.upload_domain_data(domain, domain_data, year=year, sync_latest=False)
                        
                        logger.info(f"  已上传 {domain} ({year}): {uploaded}")
                
                # 所有年度文件上传完成后，统一同步 latest.json
                logger.info("开始同步 latest.json...")
                for domain in ['sermon', 'volunteer', 'worship']:
                    try:
                        storage_manager._sync_latest_from_yearly(domain)
                        logger.info(f"✅ 已同步 {domain}/latest.json")
                    except Exception as e:
                        logger.error(f"❌ 同步 {domain}/latest.json 失败: {e}")
                
            except ImportError:
                logger.warning("google-cloud-storage 未安装，跳过云存储上传")
            except Exception as e:
                logger.error(f"上传到 Cloud Storage 失败: {e}")
        
        return saved_files
    
    def run(self, dry_run: bool = False) -> int:
        """
        运行完整的清洗管线
        
        Args:
            dry_run: 是否为干跑模式
            
        Returns:
            退出码（0 表示成功，非 0 表示有错误）
        """
        try:
            # 1. 读取原始数据
            raw_df = self.read_source_data()
            
            # 2. 清洗数据
            clean_df = self.clean_data(raw_df)
            
            # 3. 校验数据
            report = self.validate_data(clean_df)
            
            # 4. 输出结果
            self.write_output(clean_df, dry_run=dry_run)
            
            # 5. 生成服务层数据
            service_files = self.generate_service_layer(clean_df)
            
            # 6. 打印摘要
            print("\n" + "=" * 60)
            print(report.format_report(max_issues=5))
            print("=" * 60)
            
            if service_files:
                print("\n服务层数据生成:")
                for year, year_files in service_files.items():
                    print(f"  {year}:")
                    for domain, file_path in year_files.items():
                        print(f"    {domain.upper()}: {file_path}")
            
            # 7. 保存详细报告到日志
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = log_dir / f'validation_report_{timestamp}.txt'
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report.format_report(max_issues=100))
            
            logger.info(f"详细校验报告已保存: {report_path}")
            
            # 7. 返回退出码
            if report.error_rows > 0:
                logger.error(f"清洗完成但有 {report.error_rows} 行存在错误")
                return 1
            else:
                logger.info("清洗管线成功完成！")
                return 0
                
        except Exception as e:
            logger.error(f"清洗管线执行失败: {e}", exc_info=True)
            return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='教会主日事工数据清洗管线'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.json',
        help='配置文件路径'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='干跑模式：仅输出预览，不写回 Google Sheet'
    )
    
    args = parser.parse_args()
    
    # 运行管线
    pipeline = CleaningPipeline(args.config)
    exit_code = pipeline.run(dry_run=args.dry_run)
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
