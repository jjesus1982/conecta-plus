from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import redis.asyncio as redis
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.secret_key = settings.JWT_SECRET
        self.refresh_secret = settings.REFRESH_TOKEN_SECRET
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
        self.refresh_token_expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRATION_DAYS)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + self.access_token_expire
        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        })
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + self.refresh_token_expire
        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow()
        })
        return jwt.encode(to_encode, self.refresh_secret, algorithm=self.algorithm)

    def decode_token(self, token: str, is_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Decode and validate JWT token"""
        try:
            secret = self.refresh_secret if is_refresh else self.secret_key
            payload = jwt.decode(token, secret, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None

    async def blacklist_token(self, token: str, expire_seconds: int = 86400 * 7):
        """Add token to blacklist in Redis"""
        await self.redis.setex(f"blacklist:{token}", expire_seconds, "1")

    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        result = await self.redis.exists(f"blacklist:{token}")
        return result > 0

    async def store_refresh_token(self, user_id: str, refresh_token: str):
        """Store refresh token in Redis"""
        key = f"refresh_token:{user_id}"
        expire_seconds = int(self.refresh_token_expire.total_seconds())
        await self.redis.setex(key, expire_seconds, refresh_token)

    async def validate_refresh_token(self, user_id: str, refresh_token: str) -> bool:
        """Validate refresh token against stored value"""
        key = f"refresh_token:{user_id}"
        stored_token = await self.redis.get(key)
        if stored_token:
            return stored_token.decode('utf-8') == refresh_token
        return False

    async def revoke_user_tokens(self, user_id: str):
        """Revoke all tokens for a user"""
        key = f"refresh_token:{user_id}"
        await self.redis.delete(key)
