"""SCIM 2.0 API routes for BOL-CD

Implements System for Cross-domain Identity Management protocol
for automatic user provisioning from enterprise IdPs.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
from pydantic import BaseModel

from ..auth.scim import SCIMManager, SCIMUser, SCIMGroup, SCIMListResponse
from ..auth.manager import AuthManager
from .middleware import verify_role

router = APIRouter(prefix="/scim/v2", tags=["SCIM"])

# SCIM requires specific error format
def scim_error(status: int, detail: str) -> JSONResponse:
    """Return SCIM-formatted error response"""
    return JSONResponse(
        status_code=status,
        content={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "detail": detail,
            "status": status
        }
    )


# SCIM Service Provider Config
@router.get("/ServiceProviderConfig")
async def get_service_provider_config():
    """Get SCIM Service Provider Configuration"""
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "patch": {"supported": True},
        "bulk": {"supported": False, "maxOperations": 0},
        "filter": {"supported": True, "maxResults": 100},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "httpbasic",
                "name": "HTTP Basic",
                "description": "HTTP Basic Authentication"
            },
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token",
                "description": "OAuth 2.0 Bearer Token"
            }
        ]
    }


# Resource Types
@router.get("/ResourceTypes")
async def get_resource_types():
    """Get supported SCIM resource types"""
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "Resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "User",
                "name": "User",
                "endpoint": "/Users",
                "schema": "urn:ietf:params:scim:schemas:core:2.0:User"
            },
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "Group",
                "name": "Group",
                "endpoint": "/Groups",
                "schema": "urn:ietf:params:scim:schemas:core:2.0:Group"
            }
        ]
    }


# Schemas
@router.get("/Schemas")
async def get_schemas():
    """Get SCIM schemas"""
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "Resources": [
            {
                "id": "urn:ietf:params:scim:schemas:core:2.0:User",
                "name": "User",
                "description": "User Account"
            },
            {
                "id": "urn:ietf:params:scim:schemas:core:2.0:Group",
                "name": "Group",
                "description": "Group"
            }
        ]
    }


# Users CRUD
@router.get("/Users")
async def list_users(
    startIndex: int = Query(1, ge=1),
    count: int = Query(100, ge=1, le=1000),
    filter: Optional[str] = None,
    _: None = Depends(verify_role("admin"))
):
    """List SCIM users with optional filtering"""
    auth_manager = AuthManager()
    scim_manager = SCIMManager(auth_manager)
    
    db = auth_manager.get_db()
    try:
        response = scim_manager.list_users(db, startIndex, count, filter)
        return response.model_dump()
    finally:
        db.close()


@router.get("/Users/{user_id}")
async def get_user(
    user_id: str,
    _: None = Depends(verify_role("admin"))
):
    """Get a specific SCIM user"""
    auth_manager = AuthManager()
    scim_manager = SCIMManager(auth_manager)
    
    db = auth_manager.get_db()
    try:
        user = scim_manager.get_user(user_id, db)
        if not user:
            return scim_error(404, f"User {user_id} not found")
        return user.model_dump()
    finally:
        db.close()


@router.post("/Users")
async def create_user(
    user_data: Dict[str, Any],
    _: None = Depends(verify_role("admin"))
):
    """Create a new SCIM user"""
    auth_manager = AuthManager()
    scim_manager = SCIMManager(auth_manager)
    
    # Parse SCIM user from request
    try:
        scim_user = SCIMUser(**user_data)
    except Exception as e:
        return scim_error(400, f"Invalid user data: {str(e)}")
    
    db = auth_manager.get_db()
    try:
        created_user = scim_manager.create_user(scim_user, db)
        return JSONResponse(
            status_code=201,
            content=created_user.model_dump()
        )
    except Exception as e:
        return scim_error(409, f"Failed to create user: {str(e)}")
    finally:
        db.close()


@router.put("/Users/{user_id}")
async def update_user(
    user_id: str,
    user_data: Dict[str, Any],
    _: None = Depends(verify_role("admin"))
):
    """Update a SCIM user"""
    auth_manager = AuthManager()
    scim_manager = SCIMManager(auth_manager)
    
    # Parse SCIM user from request
    try:
        scim_user = SCIMUser(**user_data)
    except Exception as e:
        return scim_error(400, f"Invalid user data: {str(e)}")
    
    db = auth_manager.get_db()
    try:
        updated_user = scim_manager.update_user(user_id, scim_user, db)
        if not updated_user:
            return scim_error(404, f"User {user_id} not found")
        return updated_user.model_dump()
    finally:
        db.close()


@router.patch("/Users/{user_id}")
async def patch_user(
    user_id: str,
    patch_data: Dict[str, Any],
    _: None = Depends(verify_role("admin"))
):
    """Partially update a SCIM user"""
    auth_manager = AuthManager()
    scim_manager = SCIMManager(auth_manager)
    
    db = auth_manager.get_db()
    try:
        # Get existing user
        existing_user = scim_manager.get_user(user_id, db)
        if not existing_user:
            return scim_error(404, f"User {user_id} not found")
        
        # Apply patch operations
        # This is simplified - full SCIM PATCH is more complex
        for operation in patch_data.get("Operations", []):
            if operation.get("op") == "replace":
                path = operation.get("path", "")
                value = operation.get("value")
                
                if path == "active":
                    existing_user.active = value
                elif path == "displayName":
                    existing_user.displayName = value
                elif path == "emails":
                    existing_user.emails = value
        
        # Update user
        updated_user = scim_manager.update_user(user_id, existing_user, db)
        return updated_user.model_dump()
    finally:
        db.close()


@router.delete("/Users/{user_id}")
async def delete_user(
    user_id: str,
    _: None = Depends(verify_role("admin"))
):
    """Delete (deactivate) a SCIM user"""
    auth_manager = AuthManager()
    scim_manager = SCIMManager(auth_manager)
    
    db = auth_manager.get_db()
    try:
        success = scim_manager.delete_user(user_id, db)
        if not success:
            return scim_error(404, f"User {user_id} not found")
        return Response(status_code=204)
    finally:
        db.close()


# Groups CRUD
@router.get("/Groups")
async def list_groups(
    startIndex: int = Query(1, ge=1),
    count: int = Query(100, ge=1, le=1000),
    _: None = Depends(verify_role("admin"))
):
    """List SCIM groups"""
    scim_manager = SCIMManager()
    response = scim_manager.list_groups(startIndex, count)
    return response.model_dump()


@router.get("/Groups/{group_id}")
async def get_group(
    group_id: str,
    _: None = Depends(verify_role("admin"))
):
    """Get a specific SCIM group"""
    scim_manager = SCIMManager()
    group = scim_manager.get_group(group_id)
    if not group:
        return scim_error(404, f"Group {group_id} not found")
    return group.model_dump()


@router.post("/Groups")
async def create_group(
    group_data: Dict[str, Any],
    _: None = Depends(verify_role("admin"))
):
    """Create a new SCIM group"""
    try:
        scim_group = SCIMGroup(**group_data)
    except Exception as e:
        return scim_error(400, f"Invalid group data: {str(e)}")
    
    scim_manager = SCIMManager()
    created_group = scim_manager.create_group(scim_group)
    
    return JSONResponse(
        status_code=201,
        content=created_group.model_dump()
    )


@router.put("/Groups/{group_id}")
async def update_group(
    group_id: str,
    group_data: Dict[str, Any],
    _: None = Depends(verify_role("admin"))
):
    """Update a SCIM group"""
    try:
        scim_group = SCIMGroup(**group_data)
    except Exception as e:
        return scim_error(400, f"Invalid group data: {str(e)}")
    
    scim_manager = SCIMManager()
    updated_group = scim_manager.update_group(group_id, scim_group)
    if not updated_group:
        return scim_error(404, f"Group {group_id} not found")
    return updated_group.model_dump()


@router.delete("/Groups/{group_id}")
async def delete_group(
    group_id: str,
    _: None = Depends(verify_role("admin"))
):
    """Delete a SCIM group"""
    scim_manager = SCIMManager()
    success = scim_manager.delete_group(group_id)
    if not success:
        return scim_error(404, f"Group {group_id} not found")
    return Response(status_code=204)
