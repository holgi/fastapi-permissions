import pytest

SECURITY_SPEC = [{"OAuth2PasswordBearer": []}]

ITEM_ADD_SPECS = {
    "parameters": None,
    "responses": {
        "200": {
            "content": {"application/json": {"schema": {}}},
            "description": "Successful Response",
        }
    },
}

ITEM_SPECS = {
    "parameters": [
        {
            "in": "path",
            "name": "item_id",
            "required": True,
            "schema": {"title": "Item Id", "type": "integer"},
        }
    ],
    "responses": {
        "200": {
            "content": {"application/json": {"schema": {}}},
            "description": "Successful Response",
        },
        "422": {
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/HTTPValidationError"
                    }
                }
            },
            "description": "Validation Error",
        },
    },
}


ITEM_USE_SPECS = {
    "parameters": [
        {
            "in": "path",
            "name": "item_id",
            "required": True,
            "schema": {"title": "Item Id", "type": "integer"},
        }
    ],
    "responses": {
        "200": {
            "content": {"application/json": {"schema": {}}},
            "description": "Successful Response",
        },
        "422": {
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/HTTPValidationError"
                    }
                }
            },
            "description": "Validation Error",
        },
    },
}


ITEMS_SPECS = {
    "parameters": None,
    "responses": {
        "200": {
            "content": {"application/json": {"schema": {}}},
            "description": "Successful Response",
        }
    },
}

ME_SPECS = {
    "parameters": None,
    "responses": {
        "200": {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/User"}
                }
            },
            "description": "Successful Response",
        }
    },
}


def test_example_open_api_paths(example_app_openapi):
    """ test if the openapi paths match """

    expected = {
        "/item/add",
        "/item/{item_id}",
        "/item/{item_id}/use",
        "/items/",
        "/me/",
        "/token",
    }

    paths = example_app_openapi["paths"].keys()

    assert set(paths) == expected


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/item/add", ITEM_ADD_SPECS),
        ("/item/{item_id}", ITEM_SPECS),
        ("/item/{item_id}/use", ITEM_USE_SPECS),
        ("/items/", ITEMS_SPECS),
        ("/me/", ME_SPECS),
    ],
)
def test_example_open_api_specs(example_app_openapi, path, expected):
    """ test some specs of openapi paths """

    openapi_path_spec = example_app_openapi["paths"][path]["get"]

    assert openapi_path_spec.get("parameters", None) == expected["parameters"]
    assert openapi_path_spec.get("responses", None) == expected["responses"]
    assert openapi_path_spec.get("security", None) == SECURITY_SPEC
