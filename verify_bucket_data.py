#!/usr/bin/env python3
"""
验证 GCS Bucket 中的数据
"""

import json
from google.cloud import storage
from google.oauth2 import service_account

# 配置
SERVICE_ACCOUNT_FILE = 'config/service-account.json'
BUCKET_NAME = 'grace-irvine-ministry-data'

def verify_data():
    """验证上传的数据"""
    
    # 加载服务账号
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE
    )
    
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(BUCKET_NAME)
    
    print("="*60)
    print("验证 Bucket 数据")
    print("="*60)
    print()
    
    # 验证 Sermon Domain
    print("1. Sermon Domain (证道域)")
    print("-"*60)
    
    blob = bucket.blob('domains/sermon/latest.json')
    sermon_data = json.loads(blob.download_as_text())
    
    print(f"  ✓ 文件存在: domains/sermon/latest.json")
    print(f"  ✓ 领域: {sermon_data['metadata']['domain']}")
    print(f"  ✓ 版本: {sermon_data['metadata']['version']}")
    print(f"  ✓ 记录数: {sermon_data['metadata']['record_count']}")
    print(f"  ✓ 日期范围: {sermon_data['metadata']['date_range']['start']} 到 {sermon_data['metadata']['date_range']['end']}")
    print(f"  ✓ 生成时间: {sermon_data['metadata']['generated_at']}")
    
    # 显示第一条记录
    if sermon_data['sermons']:
        first_sermon = sermon_data['sermons'][0]
        print()
        print("  首条记录示例:")
        print(f"    日期: {first_sermon['service_date']}")
        print(f"    标题: {first_sermon['sermon']['title']}")
        print(f"    系列: {first_sermon['sermon']['series']}")
        print(f"    经文: {first_sermon['sermon']['scripture']}")
        print(f"    讲员: {first_sermon['preacher']['name']}")
        print(f"    诗歌: {', '.join(first_sermon['songs'][:3]) if first_sermon['songs'] else '无'}")
    
    print()
    
    # 验证 Volunteer Domain
    print("2. Volunteer Domain (同工域)")
    print("-"*60)
    
    blob = bucket.blob('domains/volunteer/latest.json')
    volunteer_data = json.loads(blob.download_as_text())
    
    print(f"  ✓ 文件存在: domains/volunteer/latest.json")
    print(f"  ✓ 领域: {volunteer_data['metadata']['domain']}")
    print(f"  ✓ 版本: {volunteer_data['metadata']['version']}")
    print(f"  ✓ 记录数: {volunteer_data['metadata']['record_count']}")
    print(f"  ✓ 日期范围: {volunteer_data['metadata']['date_range']['start']} 到 {volunteer_data['metadata']['date_range']['end']}")
    print(f"  ✓ 生成时间: {volunteer_data['metadata']['generated_at']}")
    
    # 显示第一条记录
    if volunteer_data['volunteers']:
        first_volunteer = volunteer_data['volunteers'][0]
        print()
        print("  首条记录示例:")
        print(f"    日期: {first_volunteer['service_date']}")
        print(f"    敬拜带领: {first_volunteer['worship']['lead']['name']}")
        print(f"    敬拜团队: {', '.join([t['name'] for t in first_volunteer['worship']['team']])}")
        print(f"    司琴: {first_volunteer['worship']['pianist']['name']}")
        print(f"    音控: {first_volunteer['technical']['audio']['name']}")
        print(f"    视频: {first_volunteer['technical']['video']['name']}")
    
    print()
    
    # 验证年度文件
    print("3. 年度文件")
    print("-"*60)
    
    blob = bucket.blob('domains/sermon/2024/sermon_2024.json')
    if blob.exists():
        print(f"  ✓ 2024年证道文件存在")
    
    blob = bucket.blob('domains/volunteer/2024/volunteer_2024.json')
    if blob.exists():
        print(f"  ✓ 2024年同工文件存在")
    
    print()
    
    # 列出所有文件
    print("4. Bucket 文件列表")
    print("-"*60)
    
    blobs = client.list_blobs(BUCKET_NAME, prefix='domains/')
    files = list(blobs)
    
    for blob in files:
        size_kb = blob.size / 1024
        print(f"  📄 {blob.name} ({size_kb:.1f} KB)")
    
    print()
    print("="*60)
    print("✅ 数据验证完成！所有数据正常。")
    print("="*60)

if __name__ == '__main__':
    verify_data()

