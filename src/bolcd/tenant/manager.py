"""
Multi-tenant management for BOL-CD.

This module provides tenant isolation, resource management, and access control
for enterprise deployments supporting multiple organizations.
"""

import uuid
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class TenantConfig:
    """Configuration for a single tenant."""
    
    # Basic info
    tenant_id: str
    name: str
    organization: str
    created_at: str
    updated_at: str
    
    # Resource limits
    max_events_per_day: int = 1000000
    max_rules: int = 1000
    max_users: int = 100
    max_api_calls_per_hour: int = 10000
    storage_quota_gb: int = 100
    
    # Feature flags
    features: Dict[str, bool] = None
    
    # SIEM connections
    siem_configs: List[Dict[str, Any]] = None
    
    # Custom settings
    settings: Dict[str, Any] = None
    
    # Status
    active: bool = True
    suspended_reason: Optional[str] = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = {
                'ml_optimization': True,
                'advanced_rules': True,
                'api_access': True,
                'siem_writeback': True,
                'custom_dashboards': False,
                'sso_integration': False,
                'audit_logs': True,
                'data_export': True,
            }
        if self.siem_configs is None:
            self.siem_configs = []
        if self.settings is None:
            self.settings = {}


class TenantManager:
    """Manages multi-tenant operations."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize tenant manager.
        
        Args:
            data_dir: Directory for tenant data storage
        """
        self.data_dir = data_dir or Path('/var/lib/bolcd/tenants')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tenants: Dict[str, TenantConfig] = {}
        self._load_tenants()
    
    def _load_tenants(self):
        """Load tenant configurations from disk."""
        config_file = self.data_dir / 'tenants.json'
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    for tenant_data in data.get('tenants', []):
                        tenant = TenantConfig(**tenant_data)
                        self.tenants[tenant.tenant_id] = tenant
                logger.info(f"Loaded {len(self.tenants)} tenants")
            except Exception as e:
                logger.error(f"Failed to load tenants: {e}")
    
    def _save_tenants(self):
        """Persist tenant configurations to disk."""
        config_file = self.data_dir / 'tenants.json'
        try:
            data = {
                'version': '1.0',
                'updated': datetime.now(timezone.utc).isoformat(),
                'tenants': [asdict(t) for t in self.tenants.values()]
            }
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.tenants)} tenants")
        except Exception as e:
            logger.error(f"Failed to save tenants: {e}")
    
    def create_tenant(self, 
                     name: str, 
                     organization: str,
                     **kwargs) -> TenantConfig:
        """
        Create a new tenant.
        
        Args:
            name: Tenant name
            organization: Organization name
            **kwargs: Additional configuration options
        
        Returns:
            Created tenant configuration
        """
        tenant_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        tenant = TenantConfig(
            tenant_id=tenant_id,
            name=name,
            organization=organization,
            created_at=now,
            updated_at=now,
            **kwargs
        )
        
        # Create tenant directory
        tenant_dir = self.data_dir / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (tenant_dir / 'data').mkdir(exist_ok=True)
        (tenant_dir / 'rules').mkdir(exist_ok=True)
        (tenant_dir / 'reports').mkdir(exist_ok=True)
        (tenant_dir / 'logs').mkdir(exist_ok=True)
        
        self.tenants[tenant_id] = tenant
        self._save_tenants()
        
        logger.info(f"Created tenant: {tenant_id} ({name})")
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        """Get tenant configuration by ID."""
        return self.tenants.get(tenant_id)
    
    def update_tenant(self, tenant_id: str, **updates) -> Optional[TenantConfig]:
        """
        Update tenant configuration.
        
        Args:
            tenant_id: Tenant ID
            **updates: Fields to update
        
        Returns:
            Updated tenant configuration or None if not found
        """
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return None
        
        # Update allowed fields
        allowed_fields = {
            'name', 'organization', 'max_events_per_day', 'max_rules',
            'max_users', 'max_api_calls_per_hour', 'storage_quota_gb',
            'features', 'settings', 'active', 'suspended_reason'
        }
        
        for field, value in updates.items():
            if field in allowed_fields and hasattr(tenant, field):
                setattr(tenant, field, value)
        
        tenant.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_tenants()
        
        logger.info(f"Updated tenant: {tenant_id}")
        return tenant
    
    def delete_tenant(self, tenant_id: str, hard_delete: bool = False) -> bool:
        """
        Delete or deactivate a tenant.
        
        Args:
            tenant_id: Tenant ID
            hard_delete: If True, permanently delete. Otherwise, just deactivate.
        
        Returns:
            True if successful
        """
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return False
        
        if hard_delete:
            # Remove from memory
            del self.tenants[tenant_id]
            
            # Archive tenant directory (don't delete immediately)
            tenant_dir = self.data_dir / tenant_id
            if tenant_dir.exists():
                archive_dir = self.data_dir / 'archived' / tenant_id
                archive_dir.parent.mkdir(parents=True, exist_ok=True)
                tenant_dir.rename(archive_dir)
            
            logger.info(f"Hard deleted tenant: {tenant_id}")
        else:
            # Soft delete - just deactivate
            tenant.active = False
            tenant.suspended_reason = "Deleted by admin"
            tenant.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Deactivated tenant: {tenant_id}")
        
        self._save_tenants()
        return True
    
    def list_tenants(self, active_only: bool = True) -> List[TenantConfig]:
        """
        List all tenants.
        
        Args:
            active_only: If True, only return active tenants
        
        Returns:
            List of tenant configurations
        """
        tenants = list(self.tenants.values())
        if active_only:
            tenants = [t for t in tenants if t.active]
        return tenants
    
    def check_quota(self, tenant_id: str, resource: str, amount: int = 1) -> bool:
        """
        Check if tenant has quota for a resource.
        
        Args:
            tenant_id: Tenant ID
            resource: Resource type ('events', 'rules', 'users', 'api_calls', 'storage')
            amount: Amount to check
        
        Returns:
            True if within quota
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant or not tenant.active:
            return False
        
        # Get current usage (simplified - in production, query from database)
        usage = self._get_resource_usage(tenant_id, resource)
        
        # Check against limits
        limits = {
            'events': tenant.max_events_per_day,
            'rules': tenant.max_rules,
            'users': tenant.max_users,
            'api_calls': tenant.max_api_calls_per_hour,
            'storage': tenant.storage_quota_gb * 1024 * 1024 * 1024  # Convert to bytes
        }
        
        limit = limits.get(resource, float('inf'))
        return (usage + amount) <= limit
    
    def _get_resource_usage(self, tenant_id: str, resource: str) -> int:
        """
        Get current resource usage for a tenant.
        
        This is a simplified implementation. In production, this would
        query actual usage from databases, metrics systems, etc.
        """
        # Placeholder implementation
        usage_file = self.data_dir / tenant_id / 'usage.json'
        if usage_file.exists():
            try:
                with open(usage_file, 'r') as f:
                    usage = json.load(f)
                    return usage.get(resource, 0)
            except Exception:
                pass
        return 0
    
    def get_tenant_dir(self, tenant_id: str, subdir: Optional[str] = None) -> Optional[Path]:
        """
        Get tenant's data directory.
        
        Args:
            tenant_id: Tenant ID
            subdir: Optional subdirectory (e.g., 'data', 'rules', 'reports')
        
        Returns:
            Path to tenant directory or None if not found
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None
        
        tenant_dir = self.data_dir / tenant_id
        if subdir:
            return tenant_dir / subdir
        return tenant_dir
    
    def add_siem_config(self, tenant_id: str, siem_type: str, config: Dict[str, Any]) -> bool:
        """
        Add SIEM configuration for a tenant.
        
        Args:
            tenant_id: Tenant ID
            siem_type: SIEM type ('splunk', 'sentinel', 'opensearch')
            config: SIEM configuration
        
        Returns:
            True if successful
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        # Encrypt sensitive data (simplified - use proper encryption in production)
        if 'token' in config:
            config['token_hash'] = hashlib.sha256(config['token'].encode()).hexdigest()[:8]
            config['token'] = '***encrypted***'
        
        siem_config = {
            'type': siem_type,
            'config': config,
            'added_at': datetime.now(timezone.utc).isoformat()
        }
        
        tenant.siem_configs.append(siem_config)
        tenant.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_tenants()
        
        logger.info(f"Added {siem_type} config for tenant: {tenant_id}")
        return True


class TenantContext:
    """Context manager for tenant-scoped operations."""
    
    def __init__(self, manager: TenantManager, tenant_id: str):
        """
        Initialize tenant context.
        
        Args:
            manager: Tenant manager instance
            tenant_id: Current tenant ID
        """
        self.manager = manager
        self.tenant_id = tenant_id
        self.tenant = manager.get_tenant(tenant_id)
        
        if not self.tenant:
            raise ValueError(f"Tenant not found: {tenant_id}")
        if not self.tenant.active:
            raise ValueError(f"Tenant is not active: {tenant_id}")
    
    def check_feature(self, feature: str) -> bool:
        """Check if a feature is enabled for this tenant."""
        return self.tenant.features.get(feature, False)
    
    def check_quota(self, resource: str, amount: int = 1) -> bool:
        """Check if tenant has quota for a resource."""
        return self.manager.check_quota(self.tenant_id, resource, amount)
    
    def get_data_dir(self, subdir: Optional[str] = None) -> Path:
        """Get tenant's data directory."""
        return self.manager.get_tenant_dir(self.tenant_id, subdir)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a tenant-specific setting."""
        return self.tenant.settings.get(key, default)


# Global tenant manager instance
_tenant_manager: Optional[TenantManager] = None


def get_tenant_manager() -> TenantManager:
    """Get or create global tenant manager instance."""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager


def get_tenant_context(tenant_id: str) -> TenantContext:
    """
    Get tenant context for a specific tenant.
    
    Args:
        tenant_id: Tenant ID (from API key, JWT token, etc.)
    
    Returns:
        TenantContext instance
    """
    manager = get_tenant_manager()
    return TenantContext(manager, tenant_id)


class TenantIsolation:
    """Enhanced tenant isolation with complete data separation"""
    
    @staticmethod
    def enforce_row_level_security(query: Any, tenant_id: str) -> Any:
        """Add tenant filter to all database queries"""
        return query.filter_by(tenant_id=tenant_id)
    
    @staticmethod
    def get_isolated_storage_path(tenant_id: str) -> Path:
        """Get completely isolated storage path for tenant"""
        # Use hashed tenant ID for security
        tenant_hash = hashlib.sha256(tenant_id.encode()).hexdigest()[:16]
        tenant_path = Path(f"./data/tenants/{tenant_hash}")
        tenant_path.mkdir(parents=True, exist_ok=True, mode=0o700)  # Restricted permissions
        return tenant_path
    
    @staticmethod
    def create_tenant_database(tenant_id: str, db_config: Dict[str, Any]) -> str:
        """Create isolated database for tenant"""
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Generate unique database name
        db_name = f"bolcd_tenant_{hashlib.md5(tenant_id.encode()).hexdigest()[:8]}"
        
        try:
            # Connect to PostgreSQL
            conn = psycopg2.connect(
                host=db_config.get("host", "localhost"),
                port=db_config.get("port", 5432),
                user=db_config.get("user", "postgres"),
                password=db_config.get("password", "")
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with conn.cursor() as cursor:
                # Create database
                cursor.execute(f"CREATE DATABASE {db_name} WITH ENCODING='UTF8'")
                
                # Create user for tenant
                tenant_user = f"user_{tenant_id[:8]}"
                tenant_pass = hashlib.sha256(f"{tenant_id}_pass".encode()).hexdigest()
                cursor.execute(f"CREATE USER {tenant_user} WITH PASSWORD '{tenant_pass}'")
                cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {tenant_user}")
            
            conn.close()
            
            # Return connection string
            return f"postgresql://{tenant_user}:{tenant_pass}@{db_config['host']}:{db_config['port']}/{db_name}"
            
        except Exception as e:
            logger.error(f"Failed to create database for tenant {tenant_id}: {e}")
            raise
    
    @staticmethod
    def encrypt_tenant_data(data: bytes, tenant_id: str) -> bytes:
        """Encrypt data using tenant-specific key"""
        from cryptography.fernet import Fernet
        import base64
        
        # Generate tenant-specific key
        key_material = hashlib.pbkdf2_hmac(
            'sha256',
            tenant_id.encode(),
            b'bolcd_salt_v1',  # Static salt for key derivation
            100000
        )
        key = base64.urlsafe_b64encode(key_material[:32])
        
        # Encrypt data
        f = Fernet(key)
        return f.encrypt(data)
    
    @staticmethod
    def decrypt_tenant_data(encrypted_data: bytes, tenant_id: str) -> bytes:
        """Decrypt data using tenant-specific key"""
        from cryptography.fernet import Fernet
        import base64
        
        # Generate tenant-specific key
        key_material = hashlib.pbkdf2_hmac(
            'sha256',
            tenant_id.encode(),
            b'bolcd_salt_v1',
            100000
        )
        key = base64.urlsafe_b64encode(key_material[:32])
        
        # Decrypt data
        f = Fernet(key)
        return f.decrypt(encrypted_data)
    
    @staticmethod
    def validate_tenant_access(tenant_id: str, user_id: str, resource: str) -> bool:
        """Validate that user has access to tenant resource"""
        manager = get_tenant_manager()
        
        # Check if tenant is active
        if not manager.is_tenant_active(tenant_id):
            return False
        
        # Check user belongs to tenant
        tenant = manager.get_tenant(tenant_id)
        if not tenant:
            return False
        
        # Check user permissions (simplified)
        # In production, this would check against a proper ACL
        user_tenants = tenant.settings.get("authorized_users", [])
        return user_id in user_tenants
    
    @staticmethod
    def audit_tenant_access(tenant_id: str, user_id: str, action: str, resource: str, success: bool):
        """Audit all tenant access attempts"""
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "success": success
        }
        
        # Write to tenant-specific audit log
        audit_path = TenantIsolation.get_isolated_storage_path(tenant_id) / "audit.jsonl"
        with open(audit_path, "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
