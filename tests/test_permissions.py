""" Tests the main api functions """

import inspect

import pytest


def dummy_principal_callable():
    return "dummy principals"


def dummy_resource_callable():
    return "dummy resource"


class DummyUser:
    def __init__(self, principals):
        from fastapi_permissions import Everyone, Authenticated

        self.principals = [Everyone] + principals
        if principals:
            self.principals.append(Authenticated)

    def __repr__(self):
        return self.principals[0]


dummy_user_john = DummyUser(["user:john", "role:user"])
dummy_user_jane = DummyUser(["user:jane", "role:user", "role:moderator"])
dummy_user_alice = DummyUser(["user:alice", "role:admin"])
dummy_user_bob = DummyUser([])


@pytest.fixture
def acl_fixture():
    from fastapi_permissions import All, Deny, Allow, Everyone, Authenticated

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


def test_configure_permissions_wraps_principal_callable(mocker):
    """ test if active_principle_funcs parameter is wrapped in "Depends" """

    mocker.patch("fastapi_permissions.Depends")

    from fastapi_permissions import Depends, configure_permissions

    configure_permissions(dummy_principal_callable)

    assert Depends.call_count == 1
    assert Depends.call_args == mocker.call(dummy_principal_callable)


def test_configure_permissions_returns_correct_signature(mocker):
    """ check the return value signature of configure_permissions """

    mocker.patch("fastapi_permissions.Depends")

    from fastapi_permissions import (
        Depends,
        permission_exception,
        configure_permissions,
        permission_dependency_factory,
    )

    partial_func = configure_permissions(dummy_principal_callable)
    parameters = inspect.signature(partial_func).parameters

    assert partial_func.func == permission_dependency_factory
    assert len(parameters) == 4
    assert parameters["permission"].default == inspect.Parameter.empty
    assert parameters["resource"].default == inspect.Parameter.empty
    assert parameters["active_principals_func"].default == Depends(
        dummy_principal_callable
    )
    assert parameters["permission_exception"].default == permission_exception


def test_configure_permissions_parameters(mocker):
    """ test the configuration options of configure_permissions """

    mocker.patch("fastapi_permissions.Depends")

    from fastapi_permissions import configure_permissions

    partial_func = configure_permissions(
        dummy_principal_callable, permission_exception="exception option"
    )
    parameters = inspect.signature(partial_func).parameters

    assert parameters["permission_exception"].default == "exception option"


def test_permission_dependency_factory_wraps_callable_resource(mocker):
    mocker.patch("fastapi_permissions.Depends")

    from fastapi_permissions import Depends, permission_dependency_factory

    permission_dependency_factory(
        "view",
        dummy_resource_callable,
        "active_principals_func",
        "permisssion_exception",
    )

    assert Depends.call_count == 2
    assert Depends.call_args_list[0] == mocker.call(dummy_resource_callable)


def test_permission_dependency_factory_returns_correct_signature(mocker):
    mocker.patch("fastapi_permissions.Depends")

    from fastapi_permissions import Depends, permission_dependency_factory

    permission_func = permission_dependency_factory(
        "view",
        dummy_resource_callable,
        "active_principals_func",
        "permisssion_exception",
    )

    assert Depends.call_count == 2
    args, kwargs = Depends.call_args_list[1]
    permission_func = args[0]
    assert callable(permission_func)

    parameters = inspect.signature(permission_func).parameters
    print(parameters)
    assert len(parameters) == 2
    assert parameters["resource"].default == Depends(dummy_resource_callable)
    assert parameters["principals"].default == "active_principals_func"


def test_permission_dependency_returns_requested_resource(mocker):
    """ If a user has a permission, the resource should be returned """
    mocker.patch("fastapi_permissions.has_permission", return_value=True)
    mocker.patch("fastapi_permissions.Depends")

    from fastapi_permissions import Depends, permission_dependency_factory

    # since the resulting permission function is wrapped in Depends()
    # we need to extract it from the mock
    permission_dependency_factory(
        "view",
        dummy_resource_callable,
        "active_principals_func",
        "permisssion_exception",
    )
    assert Depends.call_count == 2
    args, kwargs = Depends.call_args_list[1]
    permission_func = args[0]

    result = permission_func()
    assert result == Depends(dummy_resource_callable)


def test_permission_dependency_raises_exception(mocker):
    """ If a user dosen't have a permission, a exception should be raised """
    mocker.patch("fastapi_permissions.has_permission", return_value=False)
    mocker.patch("fastapi_permissions.Depends")

    from fastapi import HTTPException

    from fastapi_permissions import (
        Depends,
        permission_exception,
        permission_dependency_factory,
    )

    # since the resulting permission function is wrapped in Depends()
    # we need to extract it from the mock
    permission_func = permission_dependency_factory(
        "view",
        dummy_resource_callable,
        "active_principals_func",
        permission_exception,
    )
    assert Depends.call_count == 2
    args, kwargs = Depends.call_args_list[1]
    permission_func = args[0]

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

    result = has_permission(user.principals, permission, acl_fixture)

    key = "permissions:*" if permission == "nuke" else permission
    assert result == permission_results[user][key]


@pytest.mark.parametrize(
    "user",
    [dummy_user_john, dummy_user_jane, dummy_user_alice, dummy_user_bob],
)
def test_list_permissions(user, acl_fixture):
    """ tests the list_permissions function """
    from fastapi_permissions import list_permissions

    result = list_permissions(user.principals, acl_fixture)

    assert result == permission_results[user]
