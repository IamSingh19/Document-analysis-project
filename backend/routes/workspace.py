"""Workspace management routes with authentication"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from deps import get_db
from routes.auth import get_current_user
from models import Workspace

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workspaces", tags=["workspaces"])

@router.get("/")
async def list_workspaces(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all workspaces for current user (requires authentication)"""
    
    workspaces = db.query(Workspace).filter(
        Workspace.owner_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return [
        {
            "id": ws.id,
            "name": ws.name,
            "is_personal": ws.is_personal,
            "created_at": ws.created_at.isoformat(),
            "owner_id": ws.owner_id
        }
        for ws in workspaces
    ]

@router.post("/")
async def create_workspace(
    name: str = Query(..., min_length=1, max_length=255),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new workspace (requires authentication)"""
    
    workspace = Workspace(
        name=name,
        owner_id=current_user.id,
        is_personal=False
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    
    logger.info(f"Workspace created by user {current_user.id}: {name}")
    
    return {
        "id": workspace.id,
        "name": workspace.name,
        "is_personal": workspace.is_personal,
        "created_at": workspace.created_at.isoformat(),
        "owner_id": workspace.owner_id
    }

@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get workspace details (requires authentication)"""
    
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.owner_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    return {
        "id": workspace.id,
        "name": workspace.name,
        "is_personal": workspace.is_personal,
        "created_at": workspace.created_at.isoformat(),
        "owner_id": workspace.owner_id
    }

@router.put("/{workspace_id}")
async def update_workspace(
    workspace_id: int,
    name: str = Query(..., min_length=1, max_length=255),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update workspace (requires authentication)"""
    
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.owner_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    workspace.name = name
    db.commit()
    
    logger.info(f"Workspace updated by user {current_user.id}: {workspace_id}")
    
    return {
        "id": workspace.id,
        "name": workspace.name,
        "is_personal": workspace.is_personal,
        "created_at": workspace.created_at.isoformat(),
        "owner_id": workspace.owner_id
    }

@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete workspace (requires authentication)"""
    
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.owner_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if workspace.is_personal:
        raise HTTPException(status_code=400, detail="Cannot delete personal workspace")
    
    db.delete(workspace)
    db.commit()
    
    logger.info(f"Workspace deleted by user {current_user.id}: {workspace_id}")
    
    return {"message": "Workspace deleted successfully"}
