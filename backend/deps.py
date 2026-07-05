# Shared dependencies to avoid circular imports
from fastapi import Header, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session
import jwt
import os
import logging

logger = logging.getLogger(__name__)

def get_db():
    from main import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_token(token: str) -> Optional[int]:
    """Verify JWT token and return user ID"""
    try:
        SECRET_KEY = os.getenv("SECRET_KEY")
        ALGORITHM = "HS256"
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

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Get current authenticated user from JWT token
    
    This function is defined here to avoid circular imports.
    It verifies the JWT token and returns the authenticated user.
    """
    from models import User
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    user_id = verify_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return user
