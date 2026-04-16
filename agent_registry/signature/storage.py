import os
from pathlib import Path
from typing import Optional
from loguru import logger


class StoragePath:
    """
    存储路径工具类，用于后台公钥文件路径创建，权限设置等管理
    """
    
    BASE_DIR = os.path.join(Path(__file__).parent.parent.parent, "etc", "sign_verify", "jwks")
    
    @staticmethod
    def get_storage_path(organization: str, agent_name: str) -> str:
        """
        构造存储路径
        
        Args:
            organization: 组织名称
            agent_name: Agent名称
        
        Returns:
            str: 存储文件路径
        """
        org_dir = os.path.join(StoragePath.BASE_DIR, organization)
        return os.path.join(org_dir, f"{agent_name}.json")
    
    @staticmethod
    def get_organization_dir(organization: str) -> str:
        """
        获取组织目录路径
        
        Args:
            organization: 组织名称
        
        Returns:
            str: 组织目录路径
        """
        return os.path.join(StoragePath.BASE_DIR, organization)
    
    @staticmethod
    def ensure_directory_exists(file_path: str) -> None:
        """
        确保目录存在，如果不存在则创建
        
        Args:
            file_path: 文件路径
        """
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # 设置目录权限为700
        os.chmod(file_path_obj.parent, 0o700)
    
    @staticmethod
    def set_file_permissions(file_path: str) -> None:
        """
        设置文件权限为600
        
        Args:
            file_path: 文件路径
        """
        if os.path.exists(file_path):
            os.chmod(file_path, 0o600)
    
    @staticmethod
    def is_valid_path(file_path: str) -> bool:
        """
        验证路径是否有效
        
        Args:
            file_path: 文件路径
        
        Returns:
            bool: 路径是否有效
        """
        try:
            path_obj = Path(file_path)
            return path_obj.exists() and path_obj.is_file()
        except Exception:
            return False