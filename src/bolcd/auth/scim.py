"""SCIM 2.0 Protocol Implementation for BOL-CD

System for Cross-domain Identity Management (SCIM) enables automatic user provisioning
and deprovisioning from enterprise identity providers like Azure AD, Okta, OneLogin.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .models import User, UserDB
from .manager import AuthManager


class SCIMResource(BaseModel):
    """Base SCIM resource model"""
    schemas: List[str] = Field(default_factory=lambda: ["urn:ietf:params:scim:schemas:core:2.0:User"])
    id: str
    externalId: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class SCIMName(BaseModel):
    """SCIM name model"""
    formatted: Optional[str] = None
    familyName: Optional[str] = None
    givenName: Optional[str] = None
    middleName: Optional[str] = None


class SCIMEmail(BaseModel):
    """SCIM email model"""
    value: str
    type: Optional[str] = "work"
    primary: bool = True


class SCIMUser(SCIMResource):
    """SCIM user model"""
    userName: str
    name: Optional[SCIMName] = None
    displayName: Optional[str] = None
    emails: List[SCIMEmail] = Field(default_factory=list)
    active: bool = True
    groups: List[Dict[str, str]] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)


class SCIMGroup(SCIMResource):
    """SCIM group model"""
    schemas: List[str] = Field(default_factory=lambda: ["urn:ietf:params:scim:schemas:core:2.0:Group"])
    displayName: str
    members: List[Dict[str, str]] = Field(default_factory=list)


class SCIMListResponse(BaseModel):
    """SCIM list response model"""
    schemas: List[str] = Field(default_factory=lambda: ["urn:ietf:params:scim:api:messages:2.0:ListResponse"])
    totalResults: int
    itemsPerPage: int
    startIndex: int
    Resources: List[Any]


class SCIMError(BaseModel):
    """SCIM error response model"""
    schemas: List[str] = Field(default_factory=lambda: ["urn:ietf:params:scim:api:messages:2.0:Error"])
    detail: str
    status: int


class SCIMManager:
    """Manages SCIM operations for user and group provisioning"""
    
    def __init__(self, auth_manager: Optional[AuthManager] = None):
        self.auth_manager = auth_manager or AuthManager()
        self.groups: Dict[str, SCIMGroup] = {}
        self._init_default_groups()
    
    def _init_default_groups(self):
        """Initialize default groups"""
        default_groups = [
            {"id": "admin", "displayName": "Administrators"},
            {"id": "analyst", "displayName": "Security Analysts"},
            {"id": "viewer", "displayName": "Viewers"},
            {"id": "operator", "displayName": "Operators"}
        ]
        
        for group_data in default_groups:
            group = SCIMGroup(
                id=group_data["id"],
                displayName=group_data["displayName"],
                meta={
                    "resourceType": "Group",
                    "created": datetime.now(datetime.UTC).isoformat(),
                    "lastModified": datetime.now(datetime.UTC).isoformat(),
                    "location": f"/scim/v2/Groups/{group_data['id']}"
                }
            )
            self.groups[group.id] = group
    
    def user_to_scim(self, user: User) -> SCIMUser:
        """Convert internal user to SCIM user"""
        scim_user = SCIMUser(
            id=str(user.id),
            userName=user.username or user.email,
            displayName=user.full_name or user.email,
            emails=[SCIMEmail(value=user.email)],
            active=user.is_active,
            meta={
                "resourceType": "User",
                "created": user.created_at.isoformat() if user.created_at else datetime.now(datetime.UTC).isoformat(),
                "lastModified": user.updated_at.isoformat() if user.updated_at else datetime.now(datetime.UTC).isoformat(),
                "location": f"/scim/v2/Users/{user.id}"
            }
        )
        
        # Add name if available
        if user.full_name:
            parts = user.full_name.split(" ", 1)
            scim_user.name = SCIMName(
                formatted=user.full_name,
                givenName=parts[0] if parts else "",
                familyName=parts[1] if len(parts) > 1 else ""
            )
        
        # Add role as group membership
        if user.role:
            scim_user.groups = [{
                "value": user.role,
                "display": self.groups.get(user.role, {}).displayName if user.role in self.groups else user.role,
                "$ref": f"/scim/v2/Groups/{user.role}"
            }]
        
        return scim_user
    
    def create_user(self, scim_user: SCIMUser, db) -> SCIMUser:
        """Create a new user from SCIM request"""
        # Extract user data
        email = scim_user.emails[0].value if scim_user.emails else scim_user.userName
        full_name = scim_user.displayName
        
        if scim_user.name:
            full_name = scim_user.name.formatted or f"{scim_user.name.givenName} {scim_user.name.familyName}".strip()
        
        # Determine role from groups
        role = "user"  # default
        if scim_user.groups:
            for group in scim_user.groups:
                if group.get("value") in ["admin", "analyst", "operator"]:
                    role = group.get("value")
                    break
        
        # Create user in database
        db_user = UserDB(
            email=email,
            username=scim_user.userName,
            full_name=full_name or email,
            hashed_password="",  # SCIM users use SSO
            auth_provider="scim",
            provider_id=scim_user.externalId,
            is_active=scim_user.active,
            is_verified=True,  # SCIM users are pre-verified
            role=role,
            created_at=datetime.now(datetime.UTC)
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Convert back to SCIM format
        user = User.from_orm(db_user)
        return self.user_to_scim(user)
    
    def get_user(self, user_id: str, db) -> Optional[SCIMUser]:
        """Get a user by ID"""
        try:
            uid = int(user_id)
            user_db = db.query(UserDB).filter(UserDB.id == uid).first()
            if user_db:
                user = User.from_orm(user_db)
                return self.user_to_scim(user)
        except ValueError:
            pass
        return None
    
    def update_user(self, user_id: str, scim_user: SCIMUser, db) -> Optional[SCIMUser]:
        """Update a user"""
        try:
            uid = int(user_id)
            user_db = db.query(UserDB).filter(UserDB.id == uid).first()
            
            if not user_db:
                return None
            
            # Update fields
            if scim_user.userName:
                user_db.username = scim_user.userName
            
            if scim_user.displayName:
                user_db.full_name = scim_user.displayName
            elif scim_user.name:
                user_db.full_name = scim_user.name.formatted or f"{scim_user.name.givenName} {scim_user.name.familyName}".strip()
            
            if scim_user.emails:
                user_db.email = scim_user.emails[0].value
            
            user_db.is_active = scim_user.active
            
            # Update role from groups
            if scim_user.groups:
                for group in scim_user.groups:
                    if group.get("value") in ["admin", "analyst", "operator", "user"]:
                        user_db.role = group.get("value")
                        break
            
            user_db.updated_at = datetime.now(datetime.UTC)
            db.commit()
            db.refresh(user_db)
            
            user = User.from_orm(user_db)
            return self.user_to_scim(user)
            
        except ValueError:
            pass
        return None
    
    def delete_user(self, user_id: str, db) -> bool:
        """Delete (deactivate) a user"""
        try:
            uid = int(user_id)
            user_db = db.query(UserDB).filter(UserDB.id == uid).first()
            
            if not user_db:
                return False
            
            # Soft delete - just deactivate
            user_db.is_active = False
            user_db.updated_at = datetime.now(datetime.UTC)
            db.commit()
            return True
            
        except ValueError:
            pass
        return False
    
    def list_users(self, db, start_index: int = 1, count: int = 100, filter_str: Optional[str] = None) -> SCIMListResponse:
        """List users with optional filtering"""
        query = db.query(UserDB)
        
        # Apply filter if provided
        if filter_str:
            # Simple filter parsing for userName and email
            if "userName eq" in filter_str:
                username = filter_str.split('"')[1]
                query = query.filter(UserDB.username == username)
            elif "email eq" in filter_str:
                email = filter_str.split('"')[1]
                query = query.filter(UserDB.email == email)
        
        total = query.count()
        users_db = query.offset(start_index - 1).limit(count).all()
        
        scim_users = [self.user_to_scim(User.from_orm(u)) for u in users_db]
        
        return SCIMListResponse(
            totalResults=total,
            itemsPerPage=len(scim_users),
            startIndex=start_index,
            Resources=scim_users
        )
    
    def create_group(self, scim_group: SCIMGroup) -> SCIMGroup:
        """Create a new group"""
        scim_group.id = str(uuid.uuid4())
        scim_group.meta = {
            "resourceType": "Group",
            "created": datetime.now(datetime.UTC).isoformat(),
            "lastModified": datetime.now(datetime.UTC).isoformat(),
            "location": f"/scim/v2/Groups/{scim_group.id}"
        }
        self.groups[scim_group.id] = scim_group
        return scim_group
    
    def get_group(self, group_id: str) -> Optional[SCIMGroup]:
        """Get a group by ID"""
        return self.groups.get(group_id)
    
    def update_group(self, group_id: str, scim_group: SCIMGroup) -> Optional[SCIMGroup]:
        """Update a group"""
        if group_id not in self.groups:
            return None
        
        existing = self.groups[group_id]
        existing.displayName = scim_group.displayName
        existing.members = scim_group.members
        existing.meta["lastModified"] = datetime.now(datetime.UTC).isoformat()
        
        return existing
    
    def delete_group(self, group_id: str) -> bool:
        """Delete a group"""
        if group_id in self.groups:
            del self.groups[group_id]
            return True
        return False
    
    def list_groups(self, start_index: int = 1, count: int = 100) -> SCIMListResponse:
        """List all groups"""
        groups_list = list(self.groups.values())
        total = len(groups_list)
        
        # Paginate
        start = start_index - 1
        end = start + count
        paginated = groups_list[start:end]
        
        return SCIMListResponse(
            totalResults=total,
            itemsPerPage=len(paginated),
            startIndex=start_index,
            Resources=paginated
        )
