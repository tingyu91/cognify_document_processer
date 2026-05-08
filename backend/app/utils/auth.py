from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from app.config import settings

bearer = HTTPBearer()


def create_access_token(admin_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    return jwt.encode({"sub": admin_id, "exp": expire}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(admin_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    return jwt.encode({"sub": admin_id, "exp": expire, "type": "refresh"}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    """Dependency — validates JWT and returns admin_id. Raises 401 on failure."""
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        admin_id: str = payload.get("sub")
        if not admin_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return admin_id
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
