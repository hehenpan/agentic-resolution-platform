from loguru import logger

from app.models.models import User, UserType, UserStatus

class Permission:
    """
    Static collection of permissions.
    """
    SYSTEM_MANAGE = "system:manage"
    SYSTEM_READ = "system:read"
    
    TENANT_MANAGE = "tenant:manage"
    TENANT_READ = "tenant:read"
    
    USER_MANAGE = "user:manage"
    USER_READ = "user:read"


ROLE_PERMISSIONS = {
    UserType.ADMIN: {
        Permission.SYSTEM_MANAGE,
        Permission.SYSTEM_READ,
        Permission.TENANT_MANAGE,
        Permission.TENANT_READ,
        Permission.USER_MANAGE,
        Permission.USER_READ,
    },
    UserType.TENANT_ADMIN: {
        Permission.TENANT_READ,
        Permission.USER_MANAGE,
        Permission.USER_READ,
    },
    UserType.USER: {
        Permission.USER_READ,
    }
}


class RBACServiceBase(object):
    def __init__(self):
        pass

    def has_permission(self, user: User, permission: str, resource_tenant_id: int = None) -> bool:
        logger.error(
            "RBACServiceBase.has_permission must be implemented: permission={}",
            permission,
        )
        raise NotImplementedError("Method not implemented")

class RBACServiceSimple(RBACServiceBase):
    """
    Service to manage and evaluate Role-Based Access Control permissions,
    enforcing multi-tenant isolation.
    """
    def has_permission(self, user: User, permission: str, resource_tenant_id: int = None) -> bool:
        """
        Check if a user has a specific permission, optionally enforcing tenant boundary.
        """
        if user.status != UserStatus.ACTIVE:
            return False
            
        allowed_permissions = ROLE_PERMISSIONS.get(user.user_type, set())
        if permission not in allowed_permissions:
            return False
            
        # Enforce tenant isolation for Tenant Admin
        if user.user_type == UserType.TENANT_ADMIN:
            if resource_tenant_id is not None and user.tenant_id != resource_tenant_id:
                return False
                
        # Enforce tenant isolation for standard User
        if user.user_type == UserType.USER:
            if resource_tenant_id is not None and user.tenant_id != resource_tenant_id:
                return False
                
        return True
