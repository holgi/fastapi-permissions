import pytest


def get_with_user(url, username, client):
    response = client.post(
        "/token", data={"username": username, "password": "secret"}
    )
    data = response.json()
    headers = {"Authorization": "Bearer " + data["access_token"]}
    return client.get(url, headers=headers)


@pytest.mark.parametrize("username", ["alice", "bob"])
def test_app_get_token_valid_credentials(username, client):
    """ test the example login with valid credentials """
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
    """ test the example login with invalid credentials """
    response = client.post(
        "/token", data={"username": username, "password": password}
    )
    assert response.status_code >= 400


@pytest.mark.parametrize("username", ["alice", "bob"])
def test_app_get_me(username, client):
    """ test if a logged in user can access a restricted url """
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
        ("/item/add", "alice", True),
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
    """ test urls protected by principals, permissions and acls """
    response = get_with_user(url, username, client)
    assert response.status_code == 200 if granted else 403


# the following tests are only here to get to a high coverage rate


@pytest.mark.asyncio
async def test_app_no_token_subject():
    """ raise an error if no subject is specified in login token """
    from datetime import timedelta

    from fastapi import HTTPException

    from fastapi_permissions.example import (
        get_current_user,
        create_access_token,
    )

    token = create_access_token(data={}, expires_delta=timedelta(minutes=5))

    with pytest.raises(HTTPException):
        await get_current_user(token)


@pytest.mark.asyncio
async def test_app_token_with_fake_user():
    """ raise an error if an invalid subject is specified in login token """
    from datetime import timedelta

    from fastapi import HTTPException

    from fastapi_permissions.example import (
        get_current_user,
        create_access_token,
    )

    token = create_access_token(
        data={"sub": "unknown"}, expires_delta=timedelta(minutes=5)
    )

    with pytest.raises(HTTPException):
        await get_current_user(token)


@pytest.mark.asyncio
async def test_app_modified_token():
    """ raise an error if login token was modified """
    from datetime import timedelta

    from fastapi import HTTPException

    from fastapi_permissions.example import (
        get_current_user,
        create_access_token,
    )

    token = create_access_token(data={}, expires_delta=timedelta(minutes=5))

    with pytest.raises(HTTPException):
        await get_current_user(token[:-1])


@pytest.mark.asyncio
async def test_app_add_items_would_return_correct_value():
    """ add_items will return the correct value if someone had permission """
    from fastapi_permissions.example import add_items

    result = await add_items([])
    assert result == [{"items": "I can haz cheese?"}]


def test_get_active_principals_for_not_logged_in_user():
    """ return the correct principals for a non logged in user """
    from fastapi_permissions.example import Everyone, get_active_principals

    result = get_active_principals(None)
    assert result == [Everyone]
