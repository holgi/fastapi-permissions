Row Level Permissions for FastAPI
=================================

[![Build Status](https://travis-ci.com/holgi/fastapi-permissions.svg?branch=master)](https://travis-ci.com/holgi/fastapi-permissions)

While trying out the excellent [FastApi][] framework there was one peace missing for me: an easy, declarative way to define permissions of users (and roles/groups) on resources. Since I reall love the way [Pyramid][] handles this, I re-implemented and adapted the system for FastApi (well, you might call it a blatant rip-off).


An extremely simple and incomplete example:
-------------------------------------------

```python
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
Permission = configure_permissions(get_active_user_principals)

@app.get("/item/{item_identifier}")
async def show_item(item: Item=Permission("view", get_item)):
    return [{"item": item}]
```

For a better example install ```fastapi_permissions``` source in an virtual environment (see further below), and start a test server:

```
(permissions) $ uvicorn fastapi_permissions.example:app --reload
```

Visit <http://127.0.0.1:8000/docs> to try it out. There are two users available: "bob" and "alice", both have the password "secret".

The example is derived from the FastApi examples, so it should be familiar. New / added stuff is marked with comments in the source file `fastapi_permissions/example.py`


Why not use Scopes?
-------------------

For most applications the use of [scopes][] to determine the rights of a user is sufficient enough. So if scopes fit your application, please use them - they are already a part of the FastAPI framework.

While scopes are tied only to the state of the user, `fastapi_permissions` also
take the state of the requested resource into account.

Let's take an scientific  paper as an example: depending on the state of the submission process (like "draft", "submitted", "peer review" or "published") different users should have different permissions on viewing, editing or retracting. This could be acomplished with custom code in the path definition functions, but `fastapi_permissions` offers a method to define these constraints in a single place.

There is a second case, where `fastapi_permissions` might be the right addition to your app: If your brain is wired / preconditioned like mine to such a permission model - e.g. exposed for a long time to [Pyramid][]...

Long Story Short: Use [scopes][] until you need something different.


Concepts
--------

Since `fastapi_permissions` heavely derived from the [Pyramid][] framework, I strongly suggest to take a look at its [security documentation][pyramid_security] if anything is unclear to you.

The system depends on a couple of concepts not found in FastAPI:

- **resources**: objects that provide an *access controll list*
- **access controll lists**: a list of rules defining which *principal* has what *permission*
- **principal**: an identifier of a user or his/her associated groups/roles
- **permission**: an identifier (string) for an action on an object

### resources & access controll lists

A resource provides an access controll list via it's ```__acl__``` attribute. It can either be an property of an object or a callable. Each entry in the list is a tuple containing three values:

1. an action: ```fastapi_permissions.Allow``` or ```fastapi_permissions.Deny```
2. a principal: e.g. "role:admin" or "user:bob"
3. a permission or a tuple thereof: e.g. "edit" or ("view", "delete")

Examples:

```python
from fastapi_permissions import Allow, Deny, Authenticated, Everyone

class StaticAclResource:
    __acl__ =  [
        (Allow, Everyone, "view"),
        (Allow, "role:user", "share")
    ]

class DynamicAclResource:
    def __acl__(self):
        return [
        (Allow, Authenticated, "view"),
        (Allow, "role:user", "share"),
        (Allow, f"user:{self.owner}", "edit"),
    ]

# in contrast to pyramid, resources might be access conroll list themselves
# this can save some typing:

AclResourceAsList = [(Allow, Everyone, "view"), (Deny, "role:troll", "edit")]
```

You don't need to add any "deny-all-clause" at the end of the access controll list, this is automatically implied. All entries in a ACL are checked in *the order provided in the list*. This makes some complex configurations simple, but can sometimes be a pain in the lower back…

The two principals ```Everyone``` and ```Authenticated``` will be discussed in short time.

### users & principal identifiers

You **must provide** a function that returns the principals of the current active user. The principals is just a list of strings, identifying the user and groups/roles the user belongs to:

Example:

```python
def get_active_principals(user: User = Depends(get_current_user)):
    if user:
        # user is logged in
        principals = [Everyone, Authenticated]
        principals.extend(getattr(user, "principals", []))
    else:
        # user is not logged in
        principals = [Everyone]
    return principals
```

#### special principals

There are two special principals that also help providing access controll lists: ```Everyone``` and ```Authenticated```.

The ```Everyone``` principal should be added regardless of any other defined principals or login status, ```Authenticated``` should only be added for a user that is logged in.

### permissions

A permission is just a string that represents an action to be performed on a resource. Just make something up.

As with the special principals, there is a special permission that is usable as a wildcard: ```fastapi_permisssions.All```.


Usage
-----

There are some things you must provide before using the permissions system:

- a callable ([FastApi dependency][dependency]) that returns the principal of the logged in (active) user
- a resource with an access controll list

### Configuring the permissions system

Simple configuration with some defaults:

```python
from fastapi_permissions import configure_permissions

# must be provided
def get_active_principals(...):
    """ returns the principals of the current logged in user"""
    ...

# Permission is already wrapped in Depends()
Permission = configure_permissions(get_active_principals)
```

One configuration option is available:

- permission_exception:
    - this exception will be raised if a permission is denied
    - defaults to fastapi_permissions.permission_exception

```python
from fastapi_permissions import configure_permissions

# must be provided
def get_active_principals(...):
    """ returns the principals of the current logged in user"""
    ...

# Permission is already wrapped in Depends()
Permission = configure_permissions(
    get_active_principals,
    permission_exception

)
```

### using permissions in path operation

To use access controll in a path operation, you call the perviously configured function with a permission and the resource. If the permission is granted, the  requested resource the permission is checked on will be returned, or in this case, the acl list

```python
from fastapi_permissions import configure_permissions, Allow

# must be provided
def get_active_principals(...):
    """ returns the principals of the current logged in user"""
    ...

example_acl = [(Allow, "role:user", "view")]

# Permission is already wrapped in Depends()
Permission = configure_permissions(get_active_principals)

@app.get("/")
async def root(acls:list=Permission("view", example_acl)):
    return {"OK"}
```

Instead of using an access controll list directly, you can also provide a dependency function that might fetch a resource from a database, the resouce should provide its access controll list via the `__acl__` attribute:

```python
from fastapi_permissions import configure_permissions, Allow

# must be provided
def get_active_principals(...):
    """ returns the principals of the current logged in user"""
    ...

# fetches a resource from the database
def get_item(item_id: int):
    """ returns a resource from the database

    The resource provides an access controll list via its "__acl__" attribute.
    """
    ...

# Permission is alredy wrapped in Depends()
Permission = configure_permissions(get_active_principals)

@app.get("/item/{item_id}")
async def show_item(item:Item=Permission("view", get_item)):
    return {"item": item}
```

### helper functions

Sometimes you might want to check permissions inside a function and not as the definition of a path operation:

With ```has_permission(user_principals, permission, resource)``` you can preform the permission check programatically. The function signature can easily be remebered with something like "John eat apple?". The result will be either ```True``` or ```False```, so no need for try/except blocks \o/.

```python
from fastapi_permissions import (
    has_permission, Allow, All, Everyone, Authenticated
)

user_principals == [Everyone, Authenticated, "role:owner", "user:bob"]
apple_acl == [(Allow, "role:owner", All)]

if has_permission(user_principals, "eat", apple_acl):
    print "Yum!"
```

The other function provided is ```list_permissions(user_principals, resource)``` this will return a dict of all available permissions and a boolean value if the permission is granted or denied:

```python
from fastapi_permissions import list_permissions, Allow, All

user_principals == [Everyone, Authenticated, "role:owner", "user:bob"]
apple_acl == [(Allow, "role:owner", All)]

print(list_permissions(user_principals, apple_acl))
{"permissions:*": True}
```

Please note, that ```"permissions:*"``` is the string representation of ```fastapi_permissions.All```.


How it works
------------

The main work is done in the ```has_permissions()``` function, but the most interesting ones (at least for me) are the ```configure_permissions()``` and ```permission_dependency_factory()``` functions.

Wait. I didn't tell you about the latter one?

The ```permission()``` thingy used in the path operation definition before is actually the mentioned ```permission_dependency_factory()```. The ```configure_permissions()``` function just provisiones it with some default values using ```functools.partial```. This reduces the function signature from  ```permission_dependency_factory(permission, resource, active_principals_func, permission_exception)``` down to ```partial_function(permission, resource)```.

The ```permission_dependency_factory``` returns another function with the signature ```permission_dependency(Depends(resource), Depends(active_principals_func))```. This is the acutal signature, that ```Depends()``` uses in the path operation definition to search and inject the dependencies. The rest is just some closure magic ;-).

Or in other words: to have a nice API, the ```Depends()``` in the path operation function should only have a function signature for retrieving the active user and the resource. On the other side, when writing the code, I wanted to only specifiy the parts relevant to the path operation function: the resource and the permission. The rest is just on how to make it work.


(F.)A.Q.
--------

### Permission check on collection of resources

How to use the library with something like this: ```List[Item]=Permission("edit", get_items)```.
The question was actually issue #3 and I have written a longer answer in the issue, please have a look there.


Dev & Test virtual environment
------------------------------

There is an easy to use make command for setting up a virtual environment, installing the required packages and installing the project in an editable way.

```
$ git clone https://github.com/holgi/fastapi-permissions.git
$ cd fastapi-permissions
$ make devenv
$ source .venv/bin/activate
```

Then you can test any changes locally with ```make test```. This will stop
on the first error and not report coverage.

```
(permissions) $ make test
```

If you can also run all tests and get a coverage report with

```
(permissions) $ make coverage
```

And when ready to test everything as an installed package (bonus point if
using ```make clean``` before)

```
(permissions) $ make tox
```


Thanks
------
 - Sebastián Ramírez, for creating FastAPI
 - William, for fixing my stupid bug


[FastApi]: https://fastapi.tiangolo.com/
[dependency]: https://fastapi.tiangolo.com/tutorial/dependencies/first-steps/
[pyramid]: https://trypyramid.com
[pyramid_security]: https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/security.html
[scopes]: https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/
