#!/usr/bin/env python3
"""
生成指定年份的服务层数据
"""

import json
import sys
import argparse
from pathlib import Path
import pandas as pd

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from scripts.service_layer import ServiceLayerManager
from scripts.cloud_storage_utils import DomainStorageManager

def generate_yearly_data(year: int, upload: bool = False):
    """
    生成指定年份的服务层数据
    
    Args:
        year: 年份
        upload: 是否上传到 bucket
    """
    print("="*60)
    print(f"生成 {year} 年服务层数据")
    print("="*60)
    print()
    
    # 读取清洗层数据
    clean_file = Path('logs/clean_preview.json')
    if not clean_file.exists():
        print(f"✗ 清洗层数据不存在: {clean_file}")
        sys.exit(1)
    
    print(f"读取清洗层数据: {clean_file}")
    with open(clean_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    print(f"  总记录数: {len(df)}")
    
    # 筛选指定年份的数据
    year_str = str(year)
    df_year = df[df['service_date'].str.startswith(year_str)]
    
    if len(df_year) == 0:
        print(f"\n✗ 未找到 {year} 年的记录")
        sys.exit(1)
    
    print(f"  {year} 年记录数: {len(df_year)}")
    print(f"  日期范围: {df_year['service_date'].min()} 到 {df_year['service_date'].max()}")
    print()
    
    # 生成服务层数据
    manager = ServiceLayerManager()
    
    print("生成服务层数据...")
    domain_data_dict = manager.generate_domain_data(df_year, ['sermon', 'volunteer'])
    
    # 保存到本地
    output_dir = Path(f'logs/service_layer/{year}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    saved_files = {}
    for domain, domain_data in domain_data_dict.items():
        # 保存为年份文件
        output_file = output_dir / f'{domain}_{year}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(domain_data, f, ensure_ascii=False, indent=2)
        
        saved_files[domain] = output_file
        print(f"  ✓ {domain.upper()}: {output_file}")
        print(f"    记录数: {domain_data['metadata']['record_count']}")
    
    print()
    
    # 上传到 bucket（如果需要）
    if upload:
        print("上传到 Cloud Storage...")
        
        try:
            # 读取配置
            with open('config/config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            storage_config = config.get('service_layer', {}).get('storage', {})
            
            if storage_config.get('provider') == 'gcs':
                bucket_name = storage_config['bucket']
                base_path = storage_config.get('base_path', 'domains/')
                service_account_file = storage_config.get('service_account_file')
                
                storage_manager = DomainStorageManager(
                    bucket_name=bucket_name,
                    service_account_file=service_account_file,
                    base_path=base_path
                )
                
                for domain, domain_data in domain_data_dict.items():
                    # 上传年度文件
                    yearly_path = f"{domain}/{year}/{domain}_{year}.json"
                    gs_path = storage_manager.gcs_client.upload_json(domain_data, yearly_path)
                    print(f"  ✓ {domain.upper()}: {gs_path}")
                
                print()
                print("✅ 上传完成！")
            else:
                print("  ✗ Cloud Storage 未配置")
        
        except Exception as e:
            print(f"  ✗ 上传失败: {e}")
    
    print()
    print("="*60)
    print(f"✅ {year} 年数据生成完成！")
    print("="*60)
    print()
    print(f"本地文件: logs/service_layer/{year}/")
    for domain, file_path in saved_files.items():
        print(f"  - {file_path}")
    
    if upload:
        print()
        print(f"Bucket 文件: gs://{bucket_name}/domains/")
        for domain in domain_data_dict.keys():
            print(f"  - {domain}/{year}/{domain}_{year}.json")

def main():
    parser = argparse.ArgumentParser(description='生成指定年份的服务层数据')
    parser.add_argument('year', type=int, help='年份（如 2025）')
    parser.add_argument('--upload', action='store_true', help='上传到 Cloud Storage')
    
    args = parser.parse_args()
    
    generate_yearly_data(args.year, args.upload)

if __name__ == '__main__':
    main()

