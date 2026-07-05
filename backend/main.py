from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean, JSON, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker, relationship
from sqlalchemy.pool import QueuePool
from datetime import datetime, timedelta
from typing import Optional, List
import jwt
import os
from dotenv import load_dotenv
import logging
from bcrypt import hashpw, gensalt, checkpw
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv()

# Configure environment for model loading
import os
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['TRANSFORMERS_CACHE'] = os.path.expanduser('~/.cache/transformers')
os.environ['HF_HOME'] = os.path.expanduser('~/.cache/huggingface')

# Configuration - Validate required variables
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

# Validation
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise ValueError("SECRET_KEY must be set and at least 32 characters long")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database with proper connection pooling
# Note: SQLite doesn't support some PostgreSQL connection parameters
connect_args = {}
if "postgresql" in DATABASE_URL:
    connect_args = {"connect_timeout": 10}
elif "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool if "postgresql" in DATABASE_URL else None,
    pool_size=20 if "postgresql" in DATABASE_URL else 5,
    max_overflow=40 if "postgresql" in DATABASE_URL else 10,
    pool_pre_ping=True,
    echo=False,
    connect_args=connect_args
)

# Test connection on startup
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Connection pool event listener"""
    logger.debug("Database connection established")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Security utilities
def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    return hashpw(password.encode('utf-8'), gensalt(12)).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Import models from separate module to avoid circular imports
from models import (
    Base, User, Workspace, Document, DocumentChunk, Embedding,
    ChatSession, Message, WorkspaceMember, Analytics, AuditLog
)

# Global flag for table creation
tables_created = False

# FastAPI app
app = FastAPI(
    title="DocMind AI API",
    description="Production-grade RAG document intelligence platform",
    version="1.0.0"
)

# Add rate limiter to app
app.state.limiter = limiter

# CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    # Skip security headers for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return await call_next(request)
    
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

@app.on_event("startup")
async def startup_event():
    """Verify database connection on startup"""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✓ Database connection verified")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        raise

@app.on_event("startup")
async def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created/verified")
    except Exception as e:
        logger.error(f"✗ Table creation failed: {e}")
        raise

# Import dependencies from deps module
from deps import get_db as deps_get_db, get_current_user as deps_get_current_user

# Override get_db to use local SessionLocal
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Health check
@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"status": "ok", "version": "1.0.0"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

# Auth endpoints
from pydantic import BaseModel, EmailStr, Field

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserCreate(BaseModel):
    email: str
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=1)

def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT token with expiration"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[int]:
    """Verify JWT token and return user ID"""
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

# Use get_current_user from deps module
get_current_user = deps_get_current_user

@app.post("/auth/register", response_model=TokenResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register new user with email and password"""
    logger.info(f"Registration attempt: email={user.email}, username={user.username}")
    
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user.email) | (User.username == user.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email or username already registered"
        )
    
    # Create user with hashed password
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
    
    # Generate token
    access_token = create_access_token(db_user.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.post("/auth/login", response_model=TokenResponse)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password"""
    db_user = db.query(User).filter(User.email == user.email).first()
    
    if not db_user:
        # Generic error message to prevent user enumeration
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(user.password, db_user.hashed_password):
        logger.warning(f"Failed login attempt for {user.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")
    
    logger.info(f"User logged in: {user.email}")
    
    # Generate token
    access_token = create_access_token(db_user.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "role": current_user.role,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at
    }

# Import routers
from routes.auth import router as auth_router
from routes.documents import router as documents_router
from routes.chat import router as chat_router
from routes.search import router as search_router
from routes.workspace import router as workspace_router
from routes.analytics import router as analytics_router

# Include routers
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(search_router)
app.include_router(workspace_router)
app.include_router(analytics_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
