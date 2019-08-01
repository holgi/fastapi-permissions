import pytest

from starlette.testclient import TestClient


@pytest.fixture
def client():
    from fastapi_permissions.example import app

    return TestClient(app)


def get_with_user(url, username, client):
    response = client.post(
        "/token", data={"username": username, "password": "secret"}
    )
    data = response.json()
    headers = {"Authorization": "Bearer " + data["access_token"]}
    return client.get(url, headers=headers)


@pytest.mark.parametrize("username", ["alice", "bob"])
def test_app_get_token_good_credentials(username, client):
    response = client.post(
        "/token", data={"username": username, "password": "secret"}
    )
    print(response.text)
    assert response.status_code == 200


@pytest.mark.parametrize(
    "username, password",
    [
        ("bob", "wrong password"),
        ("bob", ""),
        ("wrong user", "secret"),
        ("", "secret"),
        ("", ""),
        ("wrong user", "wrong password"),
    ],
)
def test_app_get_token_bad_credentials(username, password, client):
    response = client.post(
        "/token", data={"username": username, "password": password}
    )
    assert response.status_code >= 400


@pytest.mark.parametrize("username", ["alice", "bob"])
def test_app_get_me(username, client):
    response = get_with_user("/me/", username, client)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == username


@pytest.mark.parametrize(
    "url, username, granted",
    [
        ("/items/", "bob", True),
        ("/items/", "alice", True),
        ("/item/add", "bob", False),
        ("/item/add", "alice", False),
        ("/item/1", "bob", True),
        ("/item/1", "alice", True),
        ("/item/2", "bob", True),
        ("/item/2", "alice", True),
        ("/item/1/use", "bob", True),
        ("/item/1/use", "alice", False),
        ("/item/2/use", "bob", True),
        ("/item/2/use", "alice", True),
    ],
)
def test_app_permissions(url, username, granted, client):
    response = get_with_user(url, username, client)
    assert response.status_code == 200 if granted else 403


# the following tests are only here to get to a high coverage rate


@pytest.mark.asyncio
async def test_app_no_token_subject():
    from datetime import timedelta
    from fastapi import HTTPException
    from fastapi_permissions.example import (
        create_access_token,
        get_current_user,
    )

    token = create_access_token(data={}, expires_delta=timedelta(minutes=5))

    with pytest.raises(HTTPException):
        await get_current_user(token)


@pytest.mark.asyncio
async def test_app_modified_token():
    from datetime import timedelta
    from fastapi import HTTPException
    from fastapi_permissions.example import (
        create_access_token,
        get_current_user,
    )

    token = create_access_token(data={}, expires_delta=timedelta(minutes=5))

    with pytest.raises(HTTPException):
        await get_current_user(token[:-1])


@pytest.mark.asyncio
async def test_app_token_with_fake_user():
    from datetime import timedelta
    from fastapi import HTTPException
    from fastapi_permissions.example import (
        create_access_token,
        get_current_user,
    )

    token = create_access_token(
        data={"sub": "unknown"}, expires_delta=timedelta(minutes=5)
    )

    with pytest.raises(HTTPException):
        await get_current_user(token)


@pytest.mark.asyncio
async def test_app_add_items_would_return_correct_value():
    from fastapi_permissions.example import add_items

    result = await add_items([])
    assert result == [{"items": "I can haz cheese?"}]
