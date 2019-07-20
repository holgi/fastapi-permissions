"flit needs a dockstring..."

__version__ = "0.0.1"

from fastapi import Depends, HTTPException
from starlette.status import HTTP_403_FORBIDDEN

from collections import namedtuple
from functools import partial
from typing import Any, Type


Allow = "ALLOW"  # constant: grant action
Deny = "DENY"  # constant: deny action

All = "*ALL*"  # constant: permission wildcard

Everyone = "sys:everyone"  #  constant: user principal for everyone
Authenticated = "sys:authenticated"  #  constant: authenticated user principal

DENY_ALL = (Deny, Everyone, All)  # constant: acl shorthand, deny anything
ALOW_ALL = (Allow, Everyone, All)  # constant: acl shorthand, allow everything

# the exception that will be raised, if no sufficient permissions are found
permission_exception = HTTPException(
    status_code=HTTP_403_FORBIDDEN,
    detail="Insufficient permissions",
    headers={"WWW-Authenticate": "Bearer"},
)

# the return data structure if a permission is granted
Context = namedtuple("Context", ["user", "permission", "resource"])


def configure_permissions(
    user_locator: Any,
    context_class: Type[Any] = Context,
    permission_exception: HTTPException = permission_exception,
):
    """ sets the basic configuration for the permissions system

    user_locator: a dependable that retrieves the current user
    context_class: the class used for returning when granting a permission
    permission_exception: the exception used if a permission is denied
    """
    user_locator = Depends(user_locator)

    return partial(
        create_permission,
        user_locator=user_locator,
        context_class=context_class,
        permission_exception=permission_exception,
    )


def create_permission(
    permission: str,
    resource: Any,
    user_locator: Any,
    context_class: Type[Any],
    permission_exception: HTTPException,
):
    """ returns a function that acts as a dependable for checking permissions

    This is the actual function used for creating the permission dependable,
    with the help of fucntools.partial in the "configure_permissions" function.
    """
    resource = Depends(resource)

    # to get the caller signature right, we need to add only the resource and
    # user dependable in the definition
    # the permission itself is available through the outer function scope
    def permission_dependable(resource=resource, user=user_locator):
        if has_permission(user, permission, resource):
            return context_class(
                user=user, permission=permission, resource=resource
            )
        raise permission_exception

    return permission_dependable


def get_all_user_principals(user: Any):
    """ augments all user principal with the system ones """
    user_principals = getattr(user, "principals", [])
    if user_principals:
        # user is logged in:
        return [Everyone, Authenticated] + user_principals
    else:
        # user is not logged in
        return [Everyone]


def normalize_acls(resource: Any):
    """ returns the acls as a list, even if __acl__ is a callable """
    acls = getattr(resource, "__acl__", None)
    if acls is None:
        return []
    if callable(acls):
        acls = acls()
    return acls


def has_permission(user: Any, requested_permission: str, resource: Any):
    """ checks if a user has the permission for a resource

    the order of the parameters can be remembered like "John eat apple"
    """
    user_principals = get_all_user_principals(user)
    acls = normalize_acls(resource)

    for action, principal, permission in acls:
        if permission in (requested_permission, All):
            if principal in user_principals:
                return action == Allow
    return False


def list_permissions(user: Any, resource: Any):
    """ lists all permissions of a user for a resouce """
    user_principals = get_all_user_principals(user)
    acls = normalize_acls(resource)

    available_permissions = {}

    for action, principal, permission in acls:
        if permission not in available_permissions:
            available_permissions[permission] = False
        if principal in user_principals:
            available_permissions[permission] = action == Allow

    return available_permissions
