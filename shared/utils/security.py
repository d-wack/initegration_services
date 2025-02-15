"""
Security utilities for all services.

This module provides security-related functionality including encryption,
authentication, and authorization that can be used across all microservices.
"""

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from cryptography.fernet import Fernet
from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from shared.utils.logging import get_logger

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# API key header
api_key_header = APIKeyHeader(name="X-API-Key")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    """Token model for authentication responses.

    Attributes:
        access_token: The JWT access token
        token_type: The type of token (usually "bearer")
        expires_in: Number of seconds until token expires
    """

    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    """Token data model for JWT payload.

    Attributes:
        sub: Subject of the token (usually user ID)
        exp: Expiration timestamp
        scope: Token scope/permissions
    """

    sub: str
    exp: datetime
    scope: Optional[str] = None


class SecurityConfig:
    """Security configuration for services.

    This class manages security-related configuration and provides
    utility methods for various security operations.

    Attributes:
        secret_key: Key used for JWT signing
        algorithm: Algorithm used for JWT signing
        access_token_expire_minutes: Token expiration time in minutes
        api_key_expire_days: API key expiration time in days
        encryption_key: Key used for Fernet encryption
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        api_key_expire_days: int = 30,
        encryption_key: Optional[str] = None,
    ) -> None:
        """Initialize security configuration.

        Args:
            secret_key: Key used for JWT signing
            algorithm: Algorithm used for JWT signing
            access_token_expire_minutes: Token expiration time in minutes
            api_key_expire_days: API key expiration time in days
            encryption_key: Key used for Fernet encryption
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.api_key_expire_days = api_key_expire_days
        self.encryption_key = encryption_key or self._generate_encryption_key()
        self.fernet = Fernet(self.encryption_key.encode())

    @staticmethod
    def _generate_encryption_key() -> str:
        """Generate a new Fernet encryption key.

        Returns:
            str: Base64-encoded 32-byte key
        """
        return base64.urlsafe_b64encode(os.urandom(32)).decode()

    def create_access_token(
        self,
        subject: Union[str, int],
        expires_delta: Optional[timedelta] = None,
        scope: Optional[str] = None,
    ) -> str:
        """Create a new JWT access token.

        Args:
            subject: Token subject (usually user ID)
            expires_delta: Optional custom expiration time
            scope: Optional token scope/permissions

        Returns:
            str: Encoded JWT token
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)

        expire = datetime.utcnow() + expires_delta
        to_encode = {
            "sub": str(subject),
            "exp": expire,
        }
        if scope:
            to_encode["scope"] = scope

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> TokenData:
        """Verify and decode a JWT token.

        Args:
            token: JWT token to verify

        Returns:
            TokenData: Decoded token data

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            return TokenData(
                sub=payload["sub"],
                exp=datetime.fromtimestamp(payload["exp"]),
                scope=payload.get("scope"),
            )
        except JWTError as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials",
            )

    def generate_api_key(self) -> str:
        """Generate a new API key.

        Returns:
            str: Generated API key
        """
        return secrets.token_urlsafe(32)

    def hash_api_key(self, api_key: str) -> str:
        """Hash an API key for storage.

        Args:
            api_key: API key to hash

        Returns:
            str: Hashed API key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    def verify_api_key(self, api_key: str, hashed_key: str) -> bool:
        """Verify an API key against its hash.

        Args:
            api_key: API key to verify
            hashed_key: Stored hash to verify against

        Returns:
            bool: True if API key is valid
        """
        return hmac.compare_digest(
            self.hash_api_key(api_key),
            hashed_key,
        )

    def encrypt_value(self, value: str) -> str:
        """Encrypt a string value.

        Args:
            value: String to encrypt

        Returns:
            str: Encrypted value
        """
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt an encrypted string value.

        Args:
            encrypted_value: String to decrypt

        Returns:
            str: Decrypted value

        Raises:
            ValueError: If decryption fails
        """
        try:
            return self.fernet.decrypt(encrypted_value.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise ValueError("Failed to decrypt value")

    def hash_password(self, password: str) -> str:
        """Hash a password.

        Args:
            password: Password to hash

        Returns:
            str: Hashed password
        """
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.

        Args:
            plain_password: Password to verify
            hashed_password: Stored hash to verify against

        Returns:
            bool: True if password is valid
        """
        return pwd_context.verify(plain_password, hashed_password)


async def get_current_user(
    security_config: SecurityConfig,
    token: str = Security(oauth2_scheme),
) -> Dict[str, Any]:
    """Get current user from JWT token.

    Args:
        security_config: Security configuration instance
        token: JWT token from request

    Returns:
        Dict[str, Any]: User data from token

    Raises:
        HTTPException: If token is invalid or expired
    """
    token_data = security_config.verify_token(token)
    if token_data.exp < datetime.utcnow():
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
        )
    return {"id": token_data.sub, "scope": token_data.scope}


async def verify_api_key(
    request: Request,
    api_key: str = Security(api_key_header),
) -> str:
    """Verify API key from request header.

    Args:
        request: FastAPI request object
        api_key: API key from request header

    Returns:
        str: API key if valid

    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is required",
        )
    
    # Here you would typically verify the API key against your database
    # This is a placeholder that should be implemented based on your storage
    return api_key 