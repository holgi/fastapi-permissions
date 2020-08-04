from datetime import datetime, timedelta
from typing import List

import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import PyJWTError
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError
from starlette.status import HTTP_401_UNAUTHORIZED

from fastapi_permissions import (
    Allow,
    Authenticated,
    Deny,
    Everyone,
    configure_permissions,
    list_permissions,
)

# >>> THIS IS NEW

# import of the new "permission" module for row level permissions


# <<<


# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# >>> THIS IS NEW

# users get a new field "principals", that contains a list with
# roles and other identifiers for the user

# <<<

fake_users_db = {
    "bob": {
        "username": "bob",
        "full_name": "Bobby Bob",
        "email": "bob@example.com",
        "hashed_password": pwd_context.hash("secret"),
        # >>> THIS IS NEW
        "principals": ["user:bob", "role:admin"],
        # <<<
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Chains",
        "email": "alicechains@example.com",
        "hashed_password": pwd_context.hash("secret"),
        # >>> THIS IS NEW
        "principals": ["user:alice"],
        # <<<
    },
}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str = None


class User(BaseModel):
    username: str
    email: str = None
    full_name: str = None

    # >>> THIS IS NEW
    # just reflects the changes in the fake_user_db
    principals: List[str] = []
    # <<<


class UserInDB(User):
    hashed_password: str


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

app = FastAPI()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def get_item(item_id: int):
    if item_id in fake_items_db:
        item_dict = fake_items_db[item_id]
        return Item(**item_dict)


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(*, data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except (PyJWTError, ValidationError):
        raise credentials_exception
    user = get_user(fake_users_db, username=username)
    if user is None:
        raise credentials_exception
    return user


# >>> THIS IS NEW

# a fake database for some cheesy items

fake_items_db = {
    1: {"name": "Stilton", "owner": "bob"},
    2: {"name": "Danish Blue", "owner": "alice"},
}


# the model class for the items most important is the __acl__ method


class Item(BaseModel):
    name: str
    owner: str

    def __acl__(self):
        """ defines who can do what to the model instance

        the function returns a list containing tuples in the form of
        (Allow or Deny, principal identifier, permission name)

        If a role is not listed (like "role:user") the access will be
        automatically deny. It's like a (Deny, Everyone, All) is automatically
        appended at the end.
        """
        return [
            (Allow, Authenticated, "view"),
            (Allow, "role:admin", "use"),
            (Allow, f"user:{self.owner}", "use"),
        ]


# for resources that don't have a corresponding model in the database
# a simple class with an "__acl__" property is defined


class ItemListResource:
    __acl__ = [(Allow, Authenticated, "view")]


# you can even use just a list

NewItemAcl = [(Deny, "user:bob", "create"), (Allow, Authenticated, "create")]


# the current user is determined by the "get_current_user" function.
# but the permissions system is not interested in the user itself, but in the
# associated principals.


def get_active_principals(user: User = Depends(get_current_user)):
    if user:
        # user is logged in
        principals = [Everyone, Authenticated]
        principals.extend(getattr(user, "principals", []))
    else:
        # user is not logged in
        principals = [Everyone]
    return principals


# We need to tell the permissions system, how to get the principals of the
# active user.
#
# "configure_permissions" returns a function that will return another function
# that can act as a dependable. Confusing? Propably, but easy to use.

Permission = configure_permissions(get_active_principals)

# <<<


@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = authenticate_user(
        fake_users_db, form_data.username, form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=400, detail="Incorrect username or password"
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


# >>> THIS IS NEW

# The most interesting part here is Permission("view", ItemListResource)"
# This function call will return a function that acts as a dependable

# If the currently logged in user has the permission "view" for the
# ItemListResource, the resource will be returned

# If the user does not have the proper permission, a HTTP_401_UNAUTHORIZED
# exception will be raised

# permission result for the fake users:
# - bob: granted
# - alice: granted


@app.get("/items/")
async def show_items(
    ilr: ItemListResource = Permission("view", ItemListResource),
    user=Depends(get_current_user),
):
    available_permissions = {
        index: list_permissions(user.principals, get_item(index))
        for index in fake_items_db
    }
    return [
        {
            "items": fake_items_db,
            "available_permissions": available_permissions,
        }
    ]


# permission result for the fake users:
# - bob: denied
# - alice: granted


@app.get("/item/add")
async def add_items(acls: list = Permission("create", NewItemAcl)):
    return [{"items": "I can haz cheese?"}]


# here is the second interesting thing: instead of using a resource class,
# a dependable can be used. This way, we can easily acces database entries

# permission result for the fake users:
# - bob: item 1: granted, item 2: granted
# - alice: item 1: granted, item 2: granted


@app.get("/item/{item_id}")
async def show_item(item: Item = Permission("view", get_item)):
    return [{"item": item}]


# permission result for the fake users:
# - bob: item 1: granted, item 2: granted
# - alice: item 1: DENIED, item 2: granted


@app.get("/item/{item_id}/use")
async def use_item(item: Item = Permission("use", get_item)):
    return [{"item": item}]


# <<<
