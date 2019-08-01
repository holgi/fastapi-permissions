""" tests for the utility functions """

import pytest


class DummyUser:
    def __init__(self, principals):
        self.principals = principals


class DummyResource:
    def __init__(self, acl):
        self.__acl__ = acl


@pytest.mark.parametrize("iterable", [[], (), {}, set()])
def test_normalize_acl_list_provided(iterable):
    """ test for acl provided directly as an iterable """
    from fastapi_permissions import normalize_acl

    assert normalize_acl(iterable) == iterable


def test_normalize_acl_without_acl_attribute():
    """ test for resource without __acl__ attribute """
    from fastapi_permissions import normalize_acl

    assert normalize_acl("without __acl__") == []


def test_normalize_acl_with_acl_attribute():
    """ test for resource with an __acl__ attribute """
    from fastapi_permissions import normalize_acl

    resource = DummyResource("acl definition")

    assert normalize_acl(resource) == "acl definition"


def test_normalize_acl_with_acl_method():
    """ test for resource with an __acl__ attribute """
    from fastapi_permissions import normalize_acl

    resource = DummyResource(lambda: "acl definition")

    assert normalize_acl(resource) == "acl definition"


def test_normalize_acl_attribute_takes_precedence():
    """ test for resource with an __acl__ attribute that are also iterables """
    from fastapi_permissions import normalize_acl

    class DummyList(list):
        __acl__ = "acl definition"

    resource = DummyList()

    assert normalize_acl(resource) == "acl definition"
