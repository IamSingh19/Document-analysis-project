"""Authentication routes with JWT support"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import jwt
import os
import logging
from bcrypt import hashpw, gensalt, checkpw
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from deps import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise ValueError("SECRET_KEY not properly configured")

# Pydantic Models
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_verified: bool
    created_at: str

class PasswordReset(BaseModel):
    email: str
    token: str
    new_password: str = Field(..., min_length=8)

class VerifyEmail(BaseModel):
    email: str
    code: str

# Helper Functions
def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    return hashpw(password.encode('utf-8'), gensalt(12)).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        return checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False

def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[int]:
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None

async def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Dependency to get current authenticated user"""
    from models import User
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    user_id = verify_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return user

# ============================================================================
# PUBLIC ENDPOINTS (No authentication required)
# ============================================================================

@router.post("/register", response_model=TokenResponse)
@limiter.limit("5/minute")
async def register(request, user: UserCreate, db: Session = Depends(get_db)):
    """Register new user with email and password"""
    from models import User, Workspace
    
    # Check if email or username exists
    existing = db.query(User).filter(
        (User.email == user.email) | (User.username == user.username)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email or username already registered"
        )
    
    # Create user
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hash_password(user.password),
        is_verified=False,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create personal workspace
    personal_ws = Workspace(
        name=f"{user.username}'s Workspace",
        owner_id=db_user.id,
        is_personal=True
    )
    db.add(personal_ws)
    db.commit()
    
    logger.info(f"New user registered: {user.email}")
    
    # Create token
    token = create_access_token(db_user.id)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request, user: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password"""
    from models import User
    
    db_user = db.query(User).filter(User.email == user.email).first()
    
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        # Generic error to prevent user enumeration
        logger.warning(f"Failed login attempt for {user.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")
    
    logger.info(f"User logged in: {user.email}")
    
    # Create token
    token = create_access_token(db_user.id)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/verify-email")
async def verify_email(data: VerifyEmail, db: Session = Depends(get_db)):
    """Verify email with code"""
    from models import User
    
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # In production, verify against sent code
    # For now, just mark as verified
    user.is_verified = True
    db.commit()
    
    return {"message": "Email verified successfully"}

@router.post("/forgot-password")
async def forgot_password(email: str, db: Session = Depends(get_db)):
    """Send password reset link"""
    from models import User
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if user exists
        return {"message": "If account exists, reset link sent to email"}
    
    # In production, send reset token via email
    reset_token = create_access_token(user.id, timedelta(hours=1))
    
    logger.info(f"Password reset requested for {email}")
    
    return {
        "message": "If account exists, reset link sent to email",
        "reset_token": reset_token  # Remove in production
    }

@router.post("/reset-password")
async def reset_password(data: PasswordReset, db: Session = Depends(get_db)):
    """Reset password with token"""
    from models import User
    
    user_id = verify_token(data.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update password
    user.hashed_password = hash_password(data.new_password)
    db.commit()
    
    logger.info(f"Password reset for user {user.id}")
    
    return {"message": "Password reset successfully"}

# ============================================================================
# PROTECTED ENDPOINTS (Authentication required)
# ============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current authenticated user's profile"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "role": current_user.role,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat()
    }

@router.post("/logout")
async def logout(current_user = Depends(get_current_user)):
    """Logout user (token will be invalidated by client)"""
    logger.info(f"User logged out: {current_user.email}")
    return {"message": "Successfully logged out"}

@router.get("/verify")
async def verify_token_endpoint(current_user = Depends(get_current_user)):
    """Verify that current token is valid"""
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email
    }
