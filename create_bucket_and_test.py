#!/usr/bin/env python3
"""
创建 GCS Bucket 并测试服务层数据上传
"""

import json
import sys
from pathlib import Path
from google.cloud import storage
from google.oauth2 import service_account

# 配置
SERVICE_ACCOUNT_FILE = 'config/service-account.json'
BUCKET_NAME = 'grace-irvine-ministry-data'
LOCATION = 'us-central1'  # 或 'asia-east1' 等

def create_bucket_if_not_exists():
    """创建 bucket（如果不存在）"""
    
    # 加载服务账号
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE
    )
    
    # 创建 Storage 客户端
    client = storage.Client(credentials=credentials)
    
    # 检查 bucket 是否存在
    bucket = client.bucket(BUCKET_NAME)
    
    if bucket.exists():
        print(f"✓ Bucket 已存在: gs://{BUCKET_NAME}")
        return bucket
    else:
        print(f"创建 bucket: gs://{BUCKET_NAME}")
        try:
            bucket = client.create_bucket(
                BUCKET_NAME,
                location=LOCATION
            )
            print(f"✓ Bucket 创建成功: gs://{BUCKET_NAME}")
            print(f"  位置: {LOCATION}")
            return bucket
        except Exception as e:
            print(f"✗ 创建 bucket 失败: {e}")
            print("\n提示: 如果 bucket 名称已被占用，请在 config/config.json 中更改 bucket 名称")
            sys.exit(1)

def test_upload():
    """测试上传文件"""
    
    print("\n" + "="*60)
    print("测试上传文件到 bucket")
    print("="*60)
    
    # 加载服务账号
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE
    )
    
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(BUCKET_NAME)
    
    # 创建测试文件
    test_data = {
        "test": "hello from grace-irvine-ministry-clean",
        "timestamp": "2024-10-07"
    }
    
    # 上传测试文件
    blob = bucket.blob('test/test.json')
    blob.upload_from_string(
        json.dumps(test_data, indent=2),
        content_type='application/json'
    )
    
    print(f"✓ 测试文件上传成功: gs://{BUCKET_NAME}/test/test.json")
    
    # 下载验证
    downloaded = blob.download_as_text()
    data = json.loads(downloaded)
    
    print(f"✓ 测试文件下载成功")
    print(f"  内容: {data}")
    
    # 删除测试文件
    blob.delete()
    print(f"✓ 测试文件已清理")
    
def main():
    print("="*60)
    print("GCS Bucket 创建和测试工具")
    print("="*60)
    print()
    
    # 检查服务账号文件
    if not Path(SERVICE_ACCOUNT_FILE).exists():
        print(f"✗ 服务账号文件不存在: {SERVICE_ACCOUNT_FILE}")
        sys.exit(1)
    
    print(f"✓ 服务账号文件: {SERVICE_ACCOUNT_FILE}")
    
    # 读取项目信息
    with open(SERVICE_ACCOUNT_FILE, 'r') as f:
        sa_data = json.load(f)
        project_id = sa_data.get('project_id')
        print(f"✓ GCP 项目: {project_id}")
    
    print()
    
    # 创建 bucket
    bucket = create_bucket_if_not_exists()
    
    # 测试上传
    test_upload()
    
    print()
    print("="*60)
    print("✅ 所有测试通过！")
    print("="*60)
    print()
    print("下一步:")
    print("  1. 运行: python3 scripts/service_layer.py --input logs/clean_preview.json --output-dir logs/service_layer")
    print("  2. 运行: python3 scripts/cloud_storage_utils.py --bucket grace-irvine-ministry-data --service-account config/service-account.json --upload logs/service_layer/sermon.json --domain sermon")
    print("  或")
    print("  3. 通过 API: curl -X POST http://localhost:8080/api/v1/service-layer/generate -H 'Content-Type: application/json' -d '{\"upload_to_bucket\": true}'")
    print()

if __name__ == '__main__':
    main()

