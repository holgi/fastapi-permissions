""" Row Level Permissions for FastAPI

This module provides an implementation for row level permissions for the
FastAPI framework. This is heavily inspired / ripped off the Pyramids Web
Framework, so all cudos to them!

extremely simple and incomplete example:

    from fastapi import Depends, FastAPI
    from fastapi.security import OAuth2PasswordBearer
    from fastapi_permissions import configure_permissions, Allow, Deny
    from pydantic import BaseModel

    app = FastAPI()
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

    class Item(BaseModel):
        name: str
        owner: str

        def __acl__(self):
            return [
                (Allow, Authenticated, "view"),
                (Allow, "role:admin", "edit"),
                (Allow, f"user:{self.owner}", "delete"),
            ]

    class User(BaseModel):
        name: str

        def principals(self):
            return [f"user:{self.name}"]

    def get_current_user(token: str = Depends(oauth2_scheme)):
        ...

    def get_active_user_principals(user:User = Depends(get_current_user)):
        ...

    def get_item(item_identifier):
        ...

    # Permission is already wrapped in Depends()
    Permissions = configure_permissions(get_active_user_principals)

    @app.get("/item/{item_identifier}")
    async def show_item(item:Item = Permission("view", get_item)):
        return [{"item": item}]
"""

__version__ = "0.2.7"

import functools
import itertools
from typing import Any

from fastapi import Depends, HTTPException
from starlette.status import HTTP_403_FORBIDDEN

# constants

Allow = "Allow"  # acl "allow" action
Deny = "Deny"  # acl "deny" action

Everyone = "system:everyone"  # user principal for everyone
Authenticated = "system:authenticated"  # authenticated user principal


class _AllPermissions:
    """ special container class for the all permissions constant

    first try was to override the __contains__ method of a str instance,
    but it turns out to be readonly...
    """

    def __contains__(self, other):
        """ returns alway true any permission """
        return True

    def __str__(self):
        """ string representation """
        return "permissions:*"


All = _AllPermissions()


DENY_ALL = (Deny, Everyone, All)  # acl shorthand, denies anything
ALOW_ALL = (Allow, Everyone, All)  # acl shorthand, allows everything


# the exception that will be raised, if no sufficient permissions are found
# can be configured in the configure_permissions() function
permission_exception = HTTPException(
    status_code=HTTP_403_FORBIDDEN,
    detail="Insufficient permissions",
    headers={"WWW-Authenticate": "Bearer"},
)


def configure_permissions(
    active_principals_func: Any,
    permission_exception: HTTPException = permission_exception,
):
    """ sets the basic configuration for the permissions system

    active_principals_func:
        a dependency that returns the principals of the current active user
    permission_exception:
        the exception used if a permission is denied

    returns: permission_dependency_factory function,
             with some parameters already provisioned
    """
    active_principals_func = Depends(active_principals_func)

    return functools.partial(
        permission_dependency_factory,
        active_principals_func=active_principals_func,
        permission_exception=permission_exception,
    )


def permission_dependency_factory(
    permission: str,
    resource: Any,
    active_principals_func: Any,
    permission_exception: HTTPException,
):
    """ returns a function that acts as a dependable for checking permissions

    This is the actual function used for creating the permission dependency,
    with the help of fucntools.partial in the "configure_permissions()"
    function.

    permission:
        the permission to check
    resource:
        the resource that will be accessed
    active_principals_func (provisioned  by configure_permissions):
        a dependency that returns the principals of the current active user
    permission_exception (provisioned  by configure_permissions):
        exception if permission is denied

    returns: dependency function for "Depends()"
    """
    if callable(resource):
        dependable_resource = Depends(resource)
    else:
        dependable_resource = Depends(lambda: resource)

    # to get the caller signature right, we need to add only the resource and
    # user dependable in the definition
    # the permission itself is available through the outer function scope
    def permission_dependency(
        resource=dependable_resource, principals=active_principals_func
    ):
        if has_permission(principals, permission, resource):
            return resource
        raise permission_exception

    return Depends(permission_dependency)


def has_permission(
    user_principals: list, requested_permission: str, resource: Any
):
    """ checks if a user has the permission for a resource

    The order of the function parameters can be remembered like "Joe eat apple"

    user_principals: the principals of a user
    requested_permission: the permission that should be checked
    resource: the object the user wants to access, must provide an ACL

    returns bool: permission granted or denied
    """
    acl = normalize_acl(resource)

    for action, principal, permissions in acl:
        if isinstance(permissions, str):
            permissions = {permissions}
        if requested_permission in permissions:
            if principal in user_principals:
                return action == Allow
    return False


def list_permissions(user_principals: list, resource: Any):
    """ lists all permissions of a user for a resouce

    user_principals: the principals of a user
    resource: the object the user wants to access, must provide an ACL

    returns dict: every available permission of the resource as key
                  and True / False as value if the permission is granted.
    """
    acl = normalize_acl(resource)

    acl_permissions = (permissions for _, _, permissions in acl)
    as_iterables = ({p} if not is_like_list(p) else p for p in acl_permissions)
    permissions = set(itertools.chain.from_iterable(as_iterables))

    return {
        str(p): has_permission(user_principals, p, acl) for p in permissions
    }


# utility functions


def normalize_acl(resource: Any):
    """ returns the access controll list for a resource

    If the resource is not an acl list itself it needs to have an "__acl__"
    attribute. If the "__acl__" attribute is a callable, it will be called and
    the result of the call returned.

    An existing __acl__ attribute takes precedence before checking if it is an
    iterable.
    """
    acl = getattr(resource, "__acl__", None)
    if callable(acl):
        return acl()
    elif acl is not None:
        return acl
    elif is_like_list(resource):
        return resource
    return []


def is_like_list(something):
    """ checks if something is iterable but not a string """
    if isinstance(something, str):
        return False
    return hasattr(something, "__iter__")
