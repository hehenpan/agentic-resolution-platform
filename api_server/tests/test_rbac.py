import pytest
from app.models.models import User, UserType, UserStatus
from app.services.rbac_service import RBACService, Permission

def test_rbac_service_admin_permissions():
    """
    Test that ADMIN has all permissions.
    """
    rbac = RBACService()
    admin_user = User(
        email="admin@example.com",
        user_id=1,
        user_type=UserType.ADMIN,
        status=UserStatus.ACTIVE,
        tenant_id=0
    )
    
    assert rbac.has_permission(admin_user, Permission.SYSTEM_MANAGE) is True
    assert rbac.has_permission(admin_user, Permission.SYSTEM_READ) is True
    assert rbac.has_permission(admin_user, Permission.TENANT_MANAGE) is True
    assert rbac.has_permission(admin_user, Permission.TENANT_READ) is True
    assert rbac.has_permission(admin_user, Permission.USER_MANAGE) is True
    assert rbac.has_permission(admin_user, Permission.USER_READ) is True


def test_rbac_service_tenant_admin_permissions():
    """
    Test that TENANT_ADMIN has only tenant/user management permissions.
    """
    rbac = RBACService()
    tenant_admin = User(
        email="tenant_admin@example.com",
        user_id=2,
        user_type=UserType.TENANT_ADMIN,
        status=UserStatus.ACTIVE,
        tenant_id=1
    )
    
    # Allowed
    assert rbac.has_permission(tenant_admin, Permission.TENANT_READ) is True
    assert rbac.has_permission(tenant_admin, Permission.USER_MANAGE) is True
    assert rbac.has_permission(tenant_admin, Permission.USER_READ) is True
    
    # Denied
    assert rbac.has_permission(tenant_admin, Permission.SYSTEM_MANAGE) is False
    assert rbac.has_permission(tenant_admin, Permission.SYSTEM_READ) is False
    assert rbac.has_permission(tenant_admin, Permission.TENANT_MANAGE) is False


def test_rbac_service_user_permissions():
    """
    Test that standard USER has only basic read permissions.
    """
    rbac = RBACService()
    user = User(
        email="user@example.com",
        user_id=3,
        user_type=UserType.USER,
        status=UserStatus.ACTIVE,
        tenant_id=1
    )
    
    # Allowed
    assert rbac.has_permission(user, Permission.USER_READ) is True
    
    # Denied
    assert rbac.has_permission(user, Permission.USER_MANAGE) is False
    assert rbac.has_permission(user, Permission.TENANT_READ) is False
    assert rbac.has_permission(user, Permission.SYSTEM_MANAGE) is False


def test_rbac_service_tenant_isolation():
    """
    Test that TENANT_ADMIN and USER permissions are isolated by tenant_id.
    """
    rbac = RBACService()
    
    tenant_admin = User(
        email="tenant_admin@example.com",
        user_id=2,
        user_type=UserType.TENANT_ADMIN,
        status=UserStatus.ACTIVE,
        tenant_id=1
    )
    
    # Operating on own tenant -> Allowed
    assert rbac.has_permission(tenant_admin, Permission.USER_MANAGE, target_tenant_id=1) is True
    
    # Operating on other tenant -> Denied
    assert rbac.has_permission(tenant_admin, Permission.USER_MANAGE, target_tenant_id=2) is False
    
    user = User(
        email="user@example.com",
        user_id=3,
        user_type=UserType.USER,
        status=UserStatus.ACTIVE,
        tenant_id=1
    )
    
    # Operating on own tenant -> Allowed
    assert rbac.has_permission(user, Permission.USER_READ, target_tenant_id=1) is True
    
    # Operating on other tenant -> Denied
    assert rbac.has_permission(user, Permission.USER_READ, target_tenant_id=2) is False


def test_rbac_service_inactive_user():
    """
    Test that INACTIVE users are always denied all permissions.
    """
    rbac = RBACService()
    
    inactive_admin = User(
        email="admin@example.com",
        user_id=1,
        user_type=UserType.ADMIN,
        status=UserStatus.INACTIVE,
        tenant_id=0
    )
    
    assert rbac.has_permission(inactive_admin, Permission.SYSTEM_MANAGE) is False
    assert rbac.has_permission(inactive_admin, Permission.USER_READ) is False
