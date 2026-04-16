from typing import Dict, Any
from fastapi import HTTPException, Request
from loguru import logger
from starlette import status
from jwt.api_jwk import PyJWK

from agent_registry.agent_registry.jwk_provider import JWKProvider, CertLoadError
from agent_registry.server import config, app, jwk_semaphore, async_hit

# ---------- JWK Endpoint ----------
jwk_provider = JWKProvider(cert_path=config.get("JWK_CERT_PATH", "cert.pem"))
jwk_kid = config.get("JWK_KID", None)

# Get JWK rate limit item
from agent_registry.server import parse_rate_limit
jwk_rate_item = parse_rate_limit('jwk')


@app.get("/.well-known/jwks.json")
async def get_jwks(request: Request):
    """
    Get JSON Web Key Set (JWKS) for JWT signature verification.
    This endpoint does not require authentication.
    """
    # Rate limit check
    if jwk_rate_item and not await async_hit(jwk_rate_item, request.client.host):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too Many Requests"
        )
    
    acquired = False
    try:
        jwk_semaphore.acquire_nowait()
        acquired = True
        jwk_set = jwk_provider.get_jwk_set()
        keys = []
        for jwk in jwk_set:
            enhanced_jwk = _enhance_jwk(jwk)
            keys.append(enhanced_jwk)
        return {"keys": keys}
    except CertLoadError as e:
        logger.error(f"Failed to load JWK: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in JWK endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
    finally:
        if acquired:
            jwk_semaphore.release()


def _enhance_jwk(jwk: PyJWK) -> Dict[str, Any]:
    """Enhance JWK with kid and key_ops fields."""
    jwk_dict = jwk._jwk_data.copy()
    if jwk_kid:
        jwk_dict["kid"] = jwk_kid
    jwk_dict["key_ops"] = ["verify"]
    return jwk_dict
