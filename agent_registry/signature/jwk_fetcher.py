import requests
from typing import Optional, Callable
from loguru import logger

from agent_registry.signature.models import JWK, JWKS
from agent_registry.signature.public_key_manager import PublicKeyManager


class JWKFetcher:
    """JWK获取器"""
    
    REQUEST_TIMEOUT = 10  # 10秒超时
    
    def __init__(self, public_key_manager: Optional[PublicKeyManager] = None):
        self.session = requests.Session()
        self.session.timeout = self.REQUEST_TIMEOUT
        self.public_key_manager = public_key_manager
    
    def fetch_jwks(self, jku: str) -> Optional[JWKS]:
        """
        从URL获取JWKS
        
        Args:
            jku: JWK Set URL
        
        Returns:
            Optional[JWKS]: JWKS对象，失败返回None
        """
        try:
            logger.info(f"Fetching JWKS from: {jku}")
            
            if not jku.startswith('https://'):
                logger.error(f"JKU must use HTTPS: {jku}")
                return None
            
            response = self.session.get(jku)
            if response.status_code != 200:
                logger.error(f"Failed to fetch JWKS, status: {response.status_code}")
                return None
            
            jwks_data = response.json()
            return JWKS(**jwks_data)
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching JWKS from: {jku}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while fetching JWKS: {e}")
            return None
        except Exception as e:
            logger.error(f"Error while fetching JWKS: {e}")
            return None
    
    def find_key_by_id(self, jwks: JWKS, kid: str) -> Optional[JWK]:
        """
        根据kid从JWKS中查找公钥
        
        Args:
            jwks: JWKS对象
            kid: 密钥ID
        
        Returns:
            Optional[JWK]: JWK对象，不存在返回None
        """
        try:
            for key in jwks.keys:
                if (key.kid == kid):
                    logger.info(f"Found key by kid: {kid}")
                    return key
            
            logger.warning(f"Key not found in JWKS: {kid}")
            return None
        except Exception as e:
            logger.error(f"Error while finding key: {e}")
            return None
    
    def fetch_from_backend(
        self,
        kid: str,
        organization: str,
        agent_name: str
    ) -> Optional[JWK]:
        """
        从后台获取公钥
        
        Args:
            kid: 密钥ID
            organization: 组织名称
            agent_name: Agent名称
        
        Returns:
            Optional[JWK]: JWK对象，不存在返回None
        """
        try:
            if not self.public_key_manager:
                logger.warning("PublicKeyManager not configured")
                return None
            
            jwk = self.public_key_manager.get_public_key(organization, agent_name, kid)
            if jwk:
                logger.info(f"Found backend key for kid: {kid}")
                return jwk
            else:
                logger.info(f"Backend key not found for kid: {kid}")
                return None
        except Exception as e:
            logger.error(f"Failed to get backend key: {e}")
            return None
    
    def create_backend_key_fetcher(
        self,
        organization: str,
        agent_name: str
    ) -> Callable[[str, str], Optional[JWK]]:
        """
        创建后台公钥获取函数（闭包），这里的organization和agent_name两个参数由外层函数提供，闭包函数作为key_provider给a2a-sdk调用
        
        Args:
            organization: 组织名称
            agent_name: Agent名称
        
        Returns:
            Callable: 接收(kid, jku)参数，返回JWK对象
        """
        def fetch_backend_key(kid: str, jku: str) -> Optional[JWK]:
            return self.fetch_from_backend(kid, organization, agent_name)
        
        return fetch_backend_key
    
    def fetch_jku_key(self, kid: str, jku: str) -> Optional[JWK]:
        """
        从jku获取公钥
        
        Args:
            jku: JWK Set URL
            kid: 密钥ID
        
        Returns:
            Optional[JWK]: JWK对象，不存在返回None
        """
        jwks = self.fetch_jwks(jku)
        if jwks:
            return self.find_key_by_id(jwks, kid)
        return None
    
    def create_combined_key_fetcher(
        self,
        organization: str,
        agent_name: str
    ) -> Callable[[str, str], Optional[JWK]]:
        """
        创建组合公钥获取函数（优先后台，其次jku）
        
        Args:
            organization: 组织名称
            agent_name: Agent名称
        
        Returns:
            Callable: 接收(jku, kid)参数，返回JWK对象
        """
        def fetch_combined_key(jku: str, kid: str) -> Optional[JWK]:
            backend_key = self.fetch_from_backend(kid, organization, agent_name)
            if backend_key:
                return backend_key
            
            jwks = self.fetch_jwks(jku)
            if jwks:
                return self.find_key_by_id(jwks, kid)
            
            return None
        
        return fetch_combined_key
