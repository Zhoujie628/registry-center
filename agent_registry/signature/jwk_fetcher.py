import requests
import base64
from typing import Optional, Callable
from loguru import logger

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

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
    ) -> Optional[str]:
        """
        从后台获取公钥（返回PEM格式）
        
        Args:
            kid: 密钥ID
            organization: 组织名称
            agent_name: Agent名称
        
        Returns:
            Optional[str]: PEM格式的公钥，不存在返回None
        """
        try:
            if not self.public_key_manager:
                logger.warning("PublicKeyManager not configured")
                return None
            
            jwk = self.public_key_manager.get_public_key(organization, agent_name, kid)
            if jwk:
                logger.info(f"Found backend key for kid: {kid}")
                return self._convert_jwk_to_pem(jwk)
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
    ) -> Callable[[str, str], Optional[str]]:
        """
        创建后台公钥获取函数（闭包）
        
        Args:
            organization: 组织名称
            agent_name: Agent名称
        
        Returns:
            Callable: 接收(jku, kid)参数，返回PEM格式的公钥字符串
        """
        def fetch_backend_key(kid: str, jku: str) -> Optional[str]:
            return self.fetch_from_backend(kid, organization, agent_name)
        
        return fetch_backend_key
    
    def fetch_jku_key(self, kid: str, jku: str) -> Optional[str]:
        """
        从jku获取公钥（返回PEM格式）
        
        Args:
            kid: 密钥ID
            jku: JWK Set URL
        
        Returns:
            Optional[str]: PEM格式的公钥，不存在返回None
        """
        jwks = self.fetch_jwks(jku)
        if jwks:
            jwk = self.find_key_by_id(jwks, kid)
            if jwk:
                return self._convert_jwk_to_pem(jwk)
        return None
    
    def _convert_jwk_to_pem(self, jwk: JWK) -> str:
        """
        将JWK转换为PEM格式
        
        Args:
            jwk: JWK对象
        
        Returns:
            str: PEM格式的公钥
        """
        try:
            if jwk.kty == 'EC':
                # 处理ECDSA密钥
                x_bytes = base64.urlsafe_b64decode(jwk.x + '=' * (-len(jwk.x) % 4))
                y_bytes = base64.urlsafe_b64decode(jwk.y + '=' * (-len(jwk.y) % 4))
                
                x_int = int.from_bytes(x_bytes, byteorder='big')
                y_int = int.from_bytes(y_bytes, byteorder='big')
                
                public_key = ec.EllipticCurvePublicNumbers(
                    x=x_int,
                    y=y_int,
                    curve=ec.SECP256R1()
                ).public_key(default_backend())
                
                pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                
                return pem.decode('utf-8')
            
            elif jwk.kty == 'RSA':
                # 处理RSA密钥
                n_bytes = base64.urlsafe_b64decode(jwk.n + '=' * (-len(jwk.n) % 4))
                e_bytes = base64.urlsafe_b64decode(jwk.e + '=' * (-len(jwk.e) % 4))
                
                n_int = int.from_bytes(n_bytes, byteorder='big')
                e_int = int.from_bytes(e_bytes, byteorder='big')
                
                from cryptography.hazmat.primitives.asymmetric import rsa
                public_key = rsa.RSAPublicNumbers(
                    n=n_int,
                    e=e_int
                ).public_key(default_backend())
                
                pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                
                return pem.decode('utf-8')
            
            else:
                raise ValueError(f"Unsupported key type: {jwk.kty}")
                
        except Exception as e:
            logger.error(f"Failed to convert JWK to PEM: {e}")
            raise
