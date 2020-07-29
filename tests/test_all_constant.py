""" tests for the _AllPermission class and All constant """


def test_all_instance():
    """ is the "All" constant an instance of "_AllPermissions" """
    from fastapi_permissions import All, _AllPermissions

    assert isinstance(All, _AllPermissions)


def test_all_permissions_contains():
    """ does "All" contain everything """
    from fastapi_permissions import All

    for something in [True, False, None, "string", [], {}, 1, All]:
        assert something in All


def test_all_permission_string():
    """ test the string representation of the "All" constan """
    from fastapi_permissions import All

    assert str(All) == "permissions:*"
