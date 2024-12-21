from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import bcrypt
import logging

# Configure logging
logger = logging.getLogger(__name__)

# JWT settings
SECRET_KEY = "your-secret-key-keep-it-secret"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__ident="2b"
)

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        # Fallback to direct bcrypt if passlib fails
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        # Fallback to direct bcrypt if passlib fails
        try:
            return bcrypt.checkpw(
                plain_password.encode(),
                hashed_password.encode()
            )
        except Exception as e:
            logger.error(f"Error in bcrypt fallback: {str(e)}")
            return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {str(e)}")
        raise

def decode_token(token: str) -> dict:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"Error decoding token: {str(e)}")
        raise

def get_current_user(credentials: str) -> dict:
    """Get the current user from JWT token."""
    try:
        token = credentials.replace("Bearer ", "")
        payload = decode_token(token)
        return payload
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise 