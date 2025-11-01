"""
Google Secret Manager 工具模块
用于安全地存储和读取动态变化的服务 tokens 和敏感信息

最佳实践:
1. 使用 Google Secret Manager 存储所有动态 tokens
2. 支持自动轮换和版本管理
3. 提供缓存机制减少 API 调用
4. 支持降级到环境变量（用于本地开发）
"""

import os
import logging
from typing import Optional, Dict
from functools import lru_cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 尝试导入 Secret Manager 客户端
try:
    from google.cloud import secretmanager
    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    SECRET_MANAGER_AVAILABLE = False
    logger.warning(
        "google-cloud-secret-manager not available. "
        "Install with: pip install google-cloud-secret-manager"
    )


class SecretManagerHelper:
    """Google Secret Manager 辅助类"""
    
    def __init__(self, project_id: Optional[str] = None):
        """
        初始化 Secret Manager 客户端
        
        Args:
            project_id: GCP 项目 ID，如果为 None 则从环境变量读取或自动检测
        """
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID')
        self.client = None
        self._cache: Dict[str, tuple] = {}  # secret_name -> (value, timestamp)
        self._cache_ttl = timedelta(minutes=5)  # 缓存 5 分钟
        
        if SECRET_MANAGER_AVAILABLE:
            try:
                if self.project_id:
                    self.client = secretmanager.SecretManagerServiceClient()
                    logger.info(f"Secret Manager client initialized for project: {self.project_id}")
                else:
                    logger.warning(
                        "GCP_PROJECT_ID not set. Secret Manager will not be available. "
                        "Fallback to environment variables."
                    )
            except Exception as e:
                logger.warning(f"Failed to initialize Secret Manager client: {e}")
                logger.info("Will fallback to environment variables")
    
    def get_secret(
        self,
        secret_name: str,
        version: str = "latest",
        fallback_env_var: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Optional[str]:
        """
        从 Secret Manager 获取 secret 值
        
        Args:
            secret_name: Secret 名称（不包含项目路径）
            version: Secret 版本，默认为 "latest"
            fallback_env_var: 如果 Secret Manager 不可用，尝试从该环境变量读取
            project_id: 可选的项目 ID（覆盖初始化时的项目 ID）
        
        Returns:
            Secret 值，如果获取失败则返回 None
        """
        # 检查缓存
        cache_key = f"{secret_name}:{version}"
        if cache_key in self._cache:
            cached_value, cached_time = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                logger.debug(f"Using cached secret: {secret_name}")
                return cached_value
            else:
                # 缓存过期，清除
                del self._cache[cache_key]
        
        # 如果没有 Secret Manager 或客户端未初始化，尝试环境变量
        if not SECRET_MANAGER_AVAILABLE or not self.client:
            if fallback_env_var:
                value = os.getenv(fallback_env_var)
                if value:
                    logger.debug(f"Using environment variable: {fallback_env_var}")
                    return value
            logger.warning(
                f"Secret Manager not available. "
                f"Trying environment variable: {fallback_env_var or secret_name}"
            )
            return os.getenv(fallback_env_var or secret_name)
        
        # 使用 Secret Manager
        try:
            project = project_id or self.project_id
            if not project:
                raise ValueError("Project ID is required for Secret Manager")
            
            # 构建完整的 secret 路径
            name = f"projects/{project}/secrets/{secret_name}/versions/{version}"
            
            # 访问 secret 版本
            response = self.client.access_secret_version(request={"name": name})
            
            # 解码 secret 值（假设是 UTF-8 编码的字符串）
            secret_value = response.payload.data.decode("UTF-8")
            
            # 更新缓存
            self._cache[cache_key] = (secret_value, datetime.now())
            
            logger.info(f"Successfully retrieved secret: {secret_name} (cached)")
            return secret_value
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret '{secret_name}' from Secret Manager: {e}")
            
            # 降级到环境变量
            if fallback_env_var:
                value = os.getenv(fallback_env_var)
                if value:
                    logger.info(f"Using fallback environment variable: {fallback_env_var}")
                    return value
            
            return None
    
    def get_token(
        self,
        token_name: str,
        fallback_env_var: Optional[str] = None
    ) -> Optional[str]:
        """
        便捷方法：获取 token（常见用例）
        
        Args:
            token_name: Token secret 名称
            fallback_env_var: 降级环境变量名
        
        Returns:
            Token 值
        """
        return self.get_secret(token_name, fallback_env_var=fallback_env_var)
    
    def clear_cache(self, secret_name: Optional[str] = None):
        """
        清除缓存
        
        Args:
            secret_name: 要清除的 secret 名称，如果为 None 则清除所有缓存
        """
        if secret_name:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{secret_name}:")]
            for key in keys_to_remove:
                del self._cache[key]
            logger.debug(f"Cleared cache for secret: {secret_name}")
        else:
            self._cache.clear()
            logger.debug("Cleared all secret cache")


# 全局实例（延迟初始化）
_secret_helper: Optional[SecretManagerHelper] = None


def get_secret_helper() -> SecretManagerHelper:
    """获取全局 Secret Manager 辅助实例"""
    global _secret_helper
    if _secret_helper is None:
        _secret_helper = SecretManagerHelper()
    return _secret_helper


def get_secret_from_manager(
    secret_name: str,
    version: str = "latest",
    fallback_env_var: Optional[str] = None
) -> Optional[str]:
    """
    便捷函数：从 Secret Manager 获取 secret
    
    Args:
        secret_name: Secret 名称
        version: Secret 版本
        fallback_env_var: 降级环境变量名
    
    Returns:
        Secret 值
    """
    helper = get_secret_helper()
    return helper.get_secret(secret_name, version, fallback_env_var)


def get_token_from_manager(
    token_name: str,
    fallback_env_var: Optional[str] = None
) -> Optional[str]:
    """
    便捷函数：获取 token
    
    Args:
        token_name: Token secret 名称
        fallback_env_var: 降级环境变量名
    
    Returns:
        Token 值
    """
    helper = get_secret_helper()
    return helper.get_token(token_name, fallback_env_var)

