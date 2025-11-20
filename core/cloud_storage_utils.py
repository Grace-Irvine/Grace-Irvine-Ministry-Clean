#!/usr/bin/env python3
"""
Cloud Storage 工具模块
用于将服务层数据上传到 Google Cloud Storage
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

try:
    from google.cloud import storage
    from google.oauth2 import service_account
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    storage = None
    service_account = None

logger = logging.getLogger(__name__)


class CloudStorageClient:
    """Google Cloud Storage 客户端"""
    
    def __init__(
        self, 
        bucket_name: str,
        service_account_file: Optional[str] = None,
        base_path: str = "domains/"
    ):
        """
        初始化 Cloud Storage 客户端
        
        Args:
            bucket_name: GCS bucket 名称
            service_account_file: 服务账号 JSON 文件路径（可选）
            base_path: 基础路径（在 bucket 内）
        """
        if not GCS_AVAILABLE:
            raise ImportError(
                "google-cloud-storage 未安装。"
                "请运行: pip install google-cloud-storage"
            )
        
        self.bucket_name = bucket_name
        self.base_path = base_path.rstrip('/') + '/'
        
        # 初始化 GCS 客户端
        if service_account_file:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file
            )
            self.client = storage.Client(credentials=credentials)
        else:
            # 使用默认凭证（如环境变量 GOOGLE_APPLICATION_CREDENTIALS）
            self.client = storage.Client()
        
        self.bucket = self.client.bucket(bucket_name)
        
        logger.info(f"Cloud Storage 客户端初始化完成: gs://{bucket_name}/{base_path}")
    
    def upload_json(
        self, 
        data: Dict[str, Any], 
        destination_path: str,
        content_type: str = 'application/json'
    ) -> str:
        """
        上传 JSON 数据到 Cloud Storage
        
        Args:
            data: 要上传的数据字典
            destination_path: 目标路径（相对于 base_path）
            content_type: 内容类型
            
        Returns:
            上传后的完整 GCS 路径
        """
        # 构建完整路径
        full_path = self.base_path + destination_path.lstrip('/')
        
        # 创建 blob
        blob = self.bucket.blob(full_path)
        
        # 转换为 JSON 字符串
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        # 上传
        blob.upload_from_string(
            json_str,
            content_type=content_type
        )
        
        # 设置元数据
        blob.metadata = {
            'uploaded_at': datetime.now(timezone.utc).isoformat(),
            'record_count': str(data.get('metadata', {}).get('record_count', 0)),
            'domain': data.get('metadata', {}).get('domain', 'unknown')
        }
        blob.patch()
        
        gs_path = f"gs://{self.bucket_name}/{full_path}"
        logger.info(f"上传成功: {gs_path} ({len(json_str)} bytes)")
        
        return gs_path
    
    def upload_file(
        self,
        local_file: Path,
        destination_path: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        上传本地文件到 Cloud Storage
        
        Args:
            local_file: 本地文件路径
            destination_path: 目标路径（相对于 base_path）
            content_type: 内容类型（自动检测）
            
        Returns:
            上传后的完整 GCS 路径
        """
        # 构建完整路径
        full_path = self.base_path + destination_path.lstrip('/')
        
        # 创建 blob
        blob = self.bucket.blob(full_path)
        
        # 自动检测 content_type
        if content_type is None:
            if str(local_file).endswith('.json'):
                content_type = 'application/json'
            elif str(local_file).endswith('.csv'):
                content_type = 'text/csv'
            else:
                content_type = 'application/octet-stream'
        
        # 上传
        blob.upload_from_filename(str(local_file), content_type=content_type)
        
        gs_path = f"gs://{self.bucket_name}/{full_path}"
        logger.info(f"上传文件成功: {gs_path}")
        
        return gs_path
    
    def download_json(self, source_path: str) -> Dict[str, Any]:
        """
        从 Cloud Storage 下载 JSON 数据
        
        Args:
            source_path: 源路径（相对于 base_path）
            
        Returns:
            解析后的数据字典
        """
        # 构建完整路径
        full_path = self.base_path + source_path.lstrip('/')
        
        # 获取 blob
        blob = self.bucket.blob(full_path)
        
        # 下载
        json_str = blob.download_as_text()
        data = json.loads(json_str)
        
        logger.info(f"下载成功: gs://{self.bucket_name}/{full_path}")
        
        return data
    
    def list_files(self, prefix: str = "") -> List[str]:
        """
        列出指定前缀的所有文件
        
        Args:
            prefix: 文件前缀（相对于 base_path）
            
        Returns:
            文件路径列表
        """
        full_prefix = self.base_path + prefix.lstrip('/')
        
        blobs = self.client.list_blobs(self.bucket_name, prefix=full_prefix)
        
        files = [blob.name for blob in blobs]
        
        logger.info(f"找到 {len(files)} 个文件，前缀: {full_prefix}")
        
        return files
    
    def exists(self, path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            path: 文件路径（相对于 base_path）
            
        Returns:
            是否存在
        """
        full_path = self.base_path + path.lstrip('/')
        blob = self.bucket.blob(full_path)
        return blob.exists()
    
    def delete(self, path: str) -> None:
        """
        删除文件
        
        Args:
            path: 文件路径（相对于 base_path）
        """
        full_path = self.base_path + path.lstrip('/')
        blob = self.bucket.blob(full_path)
        blob.delete()
        logger.info(f"已删除: gs://{self.bucket_name}/{full_path}")


class DomainStorageManager:
    """领域数据存储管理器"""
    
    def __init__(
        self,
        bucket_name: str,
        service_account_file: Optional[str] = None,
        base_path: str = "domains/"
    ):
        """
        初始化存储管理器
        
        Args:
            bucket_name: GCS bucket 名称
            service_account_file: 服务账号 JSON 文件路径
            base_path: 基础路径
        """
        self.gcs_client = CloudStorageClient(
            bucket_name,
            service_account_file,
            base_path
        )
    
    def upload_domain_data(
        self,
        domain_name: str,
        domain_data: Dict[str, Any],
        year: Optional[int] = None,
        sync_latest: bool = True,
        force_latest: bool = False
    ) -> Dict[str, str]:
        """
        上传领域数据到 Cloud Storage
        
        Args:
            domain_name: 领域名称（如 "sermon" 或 "volunteer"）
            domain_data: 领域数据字典
            year: 年份（从数据中自动提取，或手动指定）。如果 force_latest=True，则忽略年份强制上传为 latest.json
            sync_latest: 是否同步更新 latest.json
            force_latest: 是否强制上传为 latest.json（即使有年份信息）
            
        Returns:
            上传的文件路径字典
        """
        uploaded_files = {}
        
        # 如果强制为 latest，直接上传 latest.json
        if force_latest:
            latest_path = f"{domain_name}/latest.json"
            gs_path = self.gcs_client.upload_json(domain_data, latest_path)
            uploaded_files['latest'] = gs_path
            logger.info(f"已强制上传为 latest.json: {domain_name}")
            return uploaded_files
        
        # 提取年份（如果未指定且未强制为 latest）
        if year is None:
            date_range = domain_data.get('metadata', {}).get('date_range', {})
            if date_range:
                start_date = date_range.get('start', '')
                if start_date:
                    year = int(start_date.split('-')[0])
        
        # 1. 上传年度文件（如果有年份）
        if year:
            yearly_path = f"{domain_name}/{year}/{domain_name}_{year}.json"
            gs_path = self.gcs_client.upload_json(domain_data, yearly_path)
            uploaded_files['yearly'] = gs_path
            
            # 如果启用同步，更新 latest.json
            if sync_latest:
                logger.info(f"同步更新 {domain_name}/latest.json...")
                self._sync_latest_from_yearly(domain_name)
        
        # 2. 如果是 latest 数据，直接上传
        else:
            latest_path = f"{domain_name}/latest.json"
            gs_path = self.gcs_client.upload_json(domain_data, latest_path)
            uploaded_files['latest'] = gs_path
        
        logger.info(f"领域数据上传完成: {domain_name}")
        
        return uploaded_files
    
    def upload_all_domains(
        self,
        domains_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, str]]:
        """
        上传所有领域数据
        
        Args:
            domains_data: 领域数据字典，格式：{'sermon': {...}, 'volunteer': {...}}
            
        Returns:
            上传结果字典
        """
        results = {}
        
        for domain_name, domain_data in domains_data.items():
            uploaded = self.upload_domain_data(domain_name, domain_data)
            results[domain_name] = uploaded
        
        return results
    
    def _sync_latest_from_yearly(self, domain_name: str) -> None:
        """
        从年度文件同步更新 latest.json
        
        Args:
            domain_name: 领域名称
        """
        try:
            # 1. 获取所有年度文件（排除 latest.json）
            all_files = self.gcs_client.list_files(f"{domain_name}/")
            
            # 过滤年度文件：格式应该是 {domain}/{year}/{domain}_{year}.json
            # 排除 latest.json（格式是 {domain}/latest.json）
            yearly_pattern = re.compile(rf'{re.escape(domain_name)}/\d{{4}}/{re.escape(domain_name)}_\d{{4}}\.json$')
            
            # 移除 base_path 前缀进行匹配
            base_path = self.gcs_client.base_path
            yearly_files = []
            for f in all_files:
                # 移除 base_path 得到相对路径
                relative_path = f.replace(base_path, '', 1) if f.startswith(base_path) else f
                
                # 排除 latest.json
                if relative_path == f"{domain_name}/latest.json":
                    continue
                
                # 匹配年度文件格式
                if yearly_pattern.match(relative_path) or (relative_path.endswith('.json') and f'/{domain_name}_' in relative_path and len(relative_path.split('/')) == 3):
                    yearly_files.append(f)
            
            if not yearly_files:
                logger.warning(f"未找到 {domain_name} 的年度文件")
                return
            
            logger.info(f"找到 {len(yearly_files)} 个年度文件用于合并")
            
            # 2. 合并所有年度数据
            all_records = []
            all_metadata = {}

            # 确定正确的记录字段名
            if domain_name == "volunteer":
                record_field_name = "volunteers"
            elif domain_name == "worship":
                record_field_name = "services"
            else:
                record_field_name = "sermons"

            for file_path in yearly_files:
                try:
                    # 下载年度文件（file_path 已经包含完整路径，需要移除 base_path）
                    relative_path = file_path.replace(self.gcs_client.base_path, '', 1) if file_path.startswith(self.gcs_client.base_path) else file_path
                    year_data = self.gcs_client.download_json(relative_path)

                    # 合并记录 - 尝试多种可能的字段名
                    records = (year_data.get(record_field_name) or
                              year_data.get('records') or
                              year_data.get(domain_name + 's') or [])

                    if not isinstance(records, list):
                        logger.warning(f"文件 {file_path} 的记录字段不是列表: {type(records)}")
                        records = []

                    all_records.extend(records)

                    # 合并元数据（使用最新的）
                    if 'metadata' in year_data:
                        all_metadata.update(year_data['metadata'])

                except Exception as e:
                    logger.warning(f"跳过文件 {file_path}: {e}")
                    continue

            # 3. 生成合并后的数据 - 使用正确的字段名
            merged_data = {
                'metadata': {
                    **all_metadata,
                    'record_count': len(all_records),
                    'last_updated': datetime.now(timezone.utc).isoformat(),
                    'source': 'merged_from_yearly',
                    'yearly_files': yearly_files
                },
                record_field_name: all_records  # 使用 'volunteers' 或 'sermons'
            }
            
            # 移除 ID 字段 (latest 不需要 ID)
            merged_data = self._remove_ids_recursively(merged_data)
            
            # 4. 上传合并后的 latest.json
            latest_path = f"{domain_name}/latest.json"
            self.gcs_client.upload_json(merged_data, latest_path)
            
            logger.info(f"✅ 已同步 {domain_name}/latest.json (合并了 {len(yearly_files)} 个年度文件)")
            
        except Exception as e:
            logger.error(f"❌ 同步 {domain_name}/latest.json 失败: {e}")
            
    def _remove_ids_recursively(self, data: Any) -> Any:
        """
        递归移除数据中的 id 字段
        如果是只包含 name 的字典，则直接返回 name 的值（扁平化）
        
        Args:
            data: 输入数据（字典、列表或值）
            
        Returns:
            移除 id 后的数据
        """
        if isinstance(data, dict):
            # 先递归处理所有值
            new_dict = {k: self._remove_ids_recursively(v) for k, v in data.items() if k != 'id'}
            
            # 特殊处理：如果字典只剩下 'name' 一个键，且不是在某些特定字段下（可选），则直接返回 name 值
            # 这里我们做一个通用的扁平化：如果去除 id 后只剩 name，就直接返回 name
            if len(new_dict) == 1 and 'name' in new_dict:
                return new_dict['name']
                
            return new_dict
        elif isinstance(data, list):
            return [self._remove_ids_recursively(item) for item in data]
        else:
            return data
    
    
    def download_domain_data(
        self,
        domain_name: str,
        version: str = 'latest'
    ) -> Dict[str, Any]:
        """
        下载领域数据
        
        Args:
            domain_name: 领域名称
            version: 版本（'latest' 或年份如 '2024'）
            
        Returns:
            领域数据字典
        """
        if version == 'latest':
            path = f"{domain_name}/latest.json"
        else:
            path = f"{domain_name}/{version}/{domain_name}_{version}.json"
        
        return self.gcs_client.download_json(path)
    
    def list_domain_files(self, domain_name: str) -> List[str]:
        """
        列出领域的所有文件
        
        Args:
            domain_name: 领域名称
            
        Returns:
            文件列表
        """
        return self.gcs_client.list_files(f"{domain_name}/")


def main():
    """测试 Cloud Storage 功能"""
    import sys
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='Cloud Storage 工具')
    parser.add_argument('--bucket', type=str, required=True, help='GCS Bucket 名称')
    parser.add_argument('--service-account', type=str, help='服务账号 JSON 文件')
    parser.add_argument(
        '--upload',
        type=str,
        help='上传本地 JSON 文件（sermon 或 volunteer 域）'
    )
    parser.add_argument('--domain', type=str, choices=['sermon', 'volunteer', 'worship'], help='领域名称')
    parser.add_argument('--list', action='store_true', help='列出所有文件')
    
    args = parser.parse_args()
    
    if not GCS_AVAILABLE:
        print("错误: google-cloud-storage 未安装")
        print("请运行: pip install google-cloud-storage")
        sys.exit(1)
    
    # 初始化管理器
    manager = DomainStorageManager(
        bucket_name=args.bucket,
        service_account_file=args.service_account
    )
    
    # 上传文件
    if args.upload and args.domain:
        upload_file = Path(args.upload)
        
        if not upload_file.exists():
            logger.error(f"文件不存在: {upload_file}")
            sys.exit(1)
        
        # 读取 JSON 数据
        with open(upload_file, 'r', encoding='utf-8') as f:
            domain_data = json.load(f)
        
        # 上传
        result = manager.upload_domain_data(args.domain, domain_data)
        
        print("\n上传完成:")
        for key, path in result.items():
            print(f"  {key}: {path}")
    
    # 列出文件
    elif args.list:
        for domain in ['sermon', 'volunteer', 'worship']:
            print(f"\n{domain.upper()} 域文件:")
            files = manager.list_domain_files(domain)
            for file in files:
                print(f"  - {file}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

