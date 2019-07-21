""" Tests the main api functions """

import inspect
import pytest


def dummy_user_callable():
    pass


def dummy_resource_callable():
    pass


class DummyUser:
    def __init__(self, principals):
        self.principals = principals

    def __repr__(self):
        return self.principals[0] if self.principals else "Bob"


dummy_user_john = DummyUser(["user:john", "role:user"])
dummy_user_jane = DummyUser(["user:jane", "role:user", "role:moderator"])
dummy_user_alice = DummyUser(["user:alice", "role:admin"])
dummy_user_bob = DummyUser(None)


@pytest.fixture
def acl_fixture():
    from fastapi_permissions import Allow, Deny, Everyone, Authenticated, All

    yield [
        (Allow, "user:john", "view"),
        (Allow, "user:john", "edit"),
        (Allow, "user:jane", ("edit", "use")),
        (Deny, "role:user", "create"),
        (Allow, "role:moderator", "delete"),
        (Deny, Authenticated, "copy"),
        (Allow, "role:admin", All),
        (Allow, Everyone, "share"),
        (Allow, "role:moderator", "share"),
    ]


permission_results = {
    dummy_user_john: {
        "view": True,
        "edit": True,
        "use": False,
        "create": False,
        "delete": False,
        "share": True,
        "copy": False,
        "permissions:*": False,
    },
    dummy_user_jane: {
        "view": False,
        "edit": True,
        "use": True,
        "create": False,
        "delete": True,
        "share": True,
        "copy": False,
        "permissions:*": False,
    },
    dummy_user_alice: {
        "view": True,
        "edit": True,
        "use": True,
        "create": True,
        "delete": True,
        "share": True,
        "copy": False,
        "permissions:*": True,
    },
    dummy_user_bob: {
        "view": False,
        "edit": False,
        "use": False,
        "create": False,
        "delete": False,
        "share": True,
        "copy": False,
        "permissions:*": False,
    },
}


def test_configure_permissions_wraps_current_user_func(mocker):
    """ test if the curent_user_func parameter is wrapped in "Depends" """

    mocker.patch("fastapi_permissions.Depends")

    from fastapi_permissions import configure_permissions, Depends

    configure_permissions(dummy_user_callable)

    assert Depends.call_count == 1
    assert Depends.call_args == mocker.call(dummy_user_callable)


def test_configure_permissions_returns_correct_signature(mocker):
    """ check the return value signature of configure_permissions """

    mocker.patch("fastapi_permissions.Depends")

    from fastapi_permissions import (
        configure_permissions,
        permission_dependency_factory,
        Depends,
        Grant,
        permission_exception,
    )

    partial_func = configure_permissions(dummy_user_callable)
    parameters = inspect.signature(partial_func).parameters

    assert partial_func.func == permission_dependency_factory
    assert len(parameters) == 5
    assert parameters["permission"].default == inspect.Parameter.empty
    assert parameters["resource"].default == inspect.Parameter.empty
    assert parameters["current_user_func"].default == Depends(
        dummy_user_callable
    )
    assert parameters["grant_class"].default == Grant
    assert parameters["permission_exception"].default == permission_exception


def test_configure_permissions_parameters(mocker):
    """ test the configuration options of configure_permissions """

    mocker.patch("fastapi_permissions.Depends")

    from fastapi_permissions import configure_permissions

    partial_func = configure_permissions(
        dummy_user_callable,
        grant_class="grant option",
        permission_exception="exception option",
    )
    parameters = inspect.signature(partial_func).parameters

    assert parameters["grant_class"].default == "grant option"
    assert parameters["permission_exception"].default == "exception option"


def test_permission_dependency_factory_wraps_callable_resource(mocker):
    mocker.patch("fastapi_permissions.Depends")

    from fastapi_permissions import permission_dependency_factory, Depends

    permission_dependency_factory(
        "view",
        dummy_resource_callable,
        "current_user_func",
        "grant_class",
        "permisssion_exception",
    )

    assert Depends.call_count == 1
    assert Depends.call_args == mocker.call(dummy_resource_callable)


def test_permission_dependency_factory_wraps_noncallable_resource(mocker):
    mocker.patch("fastapi_permissions.Depends")

    from fastapi_permissions import permission_dependency_factory, Depends

    permission_dependency_factory(
        "view",
        "dummy_resource",
        "current_user_func",
        "grant_class",
        "permisssion_exception",
    )

    assert Depends.call_count == 1
    assert Depends.call_args != mocker.call("dummy_resource")


def test_permission_dependency_factory_returns_correct_signature(mocker):
    mocker.patch("fastapi_permissions.Depends")

    from fastapi_permissions import permission_dependency_factory, Depends

    permission_func = permission_dependency_factory(
        "view",
        dummy_resource_callable,
        "current_user_func",
        "grant_class",
        "permisssion_exception",
    )
    parameters = inspect.signature(permission_func).parameters

    assert len(parameters) == 2
    assert parameters["resource"].default == Depends(dummy_resource_callable)
    assert parameters["user"].default == "current_user_func"


def test_permission_dependency_returns_grant(mocker):
    """ If a user has a permission, a grant should be returned """
    mocker.patch("fastapi_permissions.has_permission", return_value=True)
    mocker.patch("fastapi_permissions.Depends")

    from fastapi_permissions import (
        permission_dependency_factory,
        Grant,
        Depends,
    )

    permission_func = permission_dependency_factory(
        "view",
        dummy_resource_callable,
        "current_user_func",
        Grant,
        "permisssion_exception",
    )
    result = permission_func()

    assert isinstance(result, Grant)
    print(result)
    assert result.user == "current_user_func"
    assert result.resource == Depends(dummy_resource_callable)


def test_permission_dependency_raises_exception(mocker):
    """ If a user dosen't have a permission, a exception should be raised """
    mocker.patch("fastapi_permissions.has_permission", return_value=False)

    from fastapi_permissions import (
        permission_dependency_factory,
        permission_exception,
    )
    from fastapi import HTTPException

    permission_func = permission_dependency_factory(
        "view",
        dummy_resource_callable,
        "current_user_func",
        "grant_class",
        permission_exception,
    )
    with pytest.raises(HTTPException):
        permission_func()


@pytest.mark.parametrize(
    "user",
    [dummy_user_john, dummy_user_jane, dummy_user_alice, dummy_user_bob],
)
@pytest.mark.parametrize(
    "permission",
    ["view", "edit", "use", "create", "delete", "share", "copy", "nuke"],
)
def test_has_permission(user, permission, acl_fixture):
    """ tests the has_permission function """
    from fastapi_permissions import has_permission

    result = has_permission(user, permission, acl_fixture)

    key = "permissions:*" if permission == "nuke" else permission
    assert result == permission_results[user][key]


@pytest.mark.parametrize(
    "user",
    [dummy_user_john, dummy_user_jane, dummy_user_alice, dummy_user_bob],
)
def test_list_permissions(user, acl_fixture):
    """ tests the list_permissions function """
    from fastapi_permissions import list_permissions

    result = list_permissions(user, acl_fixture)

    assert result == permission_results[user]
