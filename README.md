Row Level Permissions for FastAPI
=================================

While trying out the excellent [FastApi][] framework there was one peace missing for me: an easy, declarative way to define permissions of users (and roles/groups) on resources. Since I reall love the way [Pyramid][] handles this, I re-implemented and adapted the system for FastApi (well, you might call it a blatant rip-off).

An extremely simple and incomplete example:
-------------------------------------------

```python
from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer
from fastapi_permissions import configure_permissions, Allow, Deny, Grant
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

def get_item(item_identifier):
    ...

permissions = configure_permissions(get_current_user)

@app.get("/item/{item_identifier}")
async def show_item(grant:Grant=Depends(permission("view", get_item))):
    return [{"item": grant.resource, "user": grant.user.name}]
```

For a better example install ```fastapi_permissions``` source in an virtual environment (see further below), and start a test server:

```
(permissions) $ uvicorn example:app --reload
```

Visit <http://127.0.0.1:8000/docs> to try it out. There are two users available: "bob" and "alice", both have the password "secret".

The example is derived from the FastApi examples, so it should be familiar. New / added stuff is marked with comments.

Concepts
--------

Since this is heavely derived from the [Pyramid][] framework, I strongly suggest to take a look at its [security documentation][] if you anything is unclear.

The system depends on a couple of concepts not found in FastAPI:

- **resources**: objects that provide an *access controll list*
- **access controll lists**: a list of rules defining which *principal* has what *permission*
- **principal**: an identifier of a user or his/her associated groups/roles
- **permission**: an identifier (string) for an action on an object

### resources & access controll lists

A resource provides an access controll list via it's ```__acl__``` attribute. It can either be an property of an object or a callable. Each entry in the list is a tuple containing three values: 

1. an action: ```fastapi_permissions.Allow``` or ```fastapi_permissions.Deny```
2. a principal: e.g. "role:admin" or "user:bob"
3. a permission or a tuple of permissions: e.g. "edit" or ("view", "delete")

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

You don't need to add any "deny-all-clause" at the end of the access controll list, this is automagically implied. All entries in a ACL are checked in *the order provided in the list*. This makes some complex configurations simple, but can sometimes be a pain in the lower back…

The two principals ```Everyone``` and ```Authenticated``` will be discussed in short time.

### users & principal identifiers

A currently logged in user **must provide** his/her principals as an attribute (as with resources, it might be a callable). The principals is just a list of strings, identifying the user and groups/roles the user belongs to:

Examples:

```python
class UserPrincipalsProperty:
	principlas = ["user:bob", "role:admin", "group:team"]

class UserPrincipalsMethod:
    def principals(self):
        return [f"account:{self.id}", "role:user"]
```

#### special principals

There are two special principals that also help providing access controll lists: ```Everyone``` and ```Authenticated```. 

If a user object doesn't provide principals (no property or empty list), the user is considered to be *not logged in*.

The ```Everyone``` principal is added regardless of any other defined principals or login status, ```Authenticated``` is only added for a user that is logged in.

### permissions

A permission is just a string that represents an action to be performed on a resource. Just make something up.

As with the special principals, there is a special permission that is usable as a wildcard: ```fastapi_permisssions.All```.

Usage
-----

There are some things you must provide before using the permissions system:

- a callable ([FastApi dependency][dependency]) that returns the active logged in user
- the user returned by the callable must provide its principals
- a resource with an access controll list

### Configuring the permissions system

Simple configuration with some defaults:

```python
from fastapi_permissions import configure_permissions

# must be provided
def get_current_user(...):
    """ returns the current logged in user"""
    ...

permission = configure_permissions(get_current_user)
```

Full configuration options are available:

- grant_class:
	- an instance of this class is returned when a permission is granted
	- must accept "user" and "resource" keyword argument in __init__
	- defaults to fastapi_permissions.Grant
- permission_exception:
	- this exception will be raised if a permission is denied
	- defaults to fastapi_permissions.permission_exception

```python
from fastapi_permissions import configure_permissions

# must be provided
def get_current_user(...):
    """ returns the current logged in user"""
    ...

permission = configure_permissions(
    get_current_user,
	grant_class,
    permission_exception

)
```

### using permissions in path operation

To use access controll in a path operation, you call the perviously configured function with a permission and the resource. If the permission is granted, a grant object will be returned. The currently active user (acquired via ```get_current_user()```) and the resource the permission is checked on are available as properties.

```python
from fastapi_permissions import configure_permissions, Allow, Grant

# must be provided
def get_current_user(...):
    """ returns the current logged in user"""
    ...

example_acl = [(Allow "role:user", "view")]
    
permission = configure_permissions(get_current_user)

@app.get("/")
async def root(grant:Grant=Depends(permission("view", example_acl))):
    return {"user": grant.user}
```

Instead of using an access controll list directly, you can also provide a dependency function that might fetch something from a database:

```python
from fastapi_permissions import configure_permissions, Allow, Grant

# must be provided
def get_current_user(...):
    """ returns the current logged in user"""
    ...

# fetches a resource from the database
def get_item(item_id: int):
    """ returns a resource from the database """
    ...
    
permission = configure_permissions(get_current_user)

@app.get("/item/{item_id}")
async def show_item(grant:Grant=Depends(permission("view", get_item))):
    return {"user": grant.user, "item": grant.resouce}
```

### helper functions

Sometimes you might want to check permissions inside a function and not as the definition of a path operation:

With ```has_permission(user, permission, resource)``` you can preform the permission check programatically. The function signature can easily be remebered with something like "John eat apple?". The result will be either ```True``` or ```False```, so no need for try/except blocks \o/.

```python
from fastapi_permissions import has_permission, Allow, All

user_john.principals == ["role:owner"]
apple_resource.__acl__ == [(Allow, "role:owner", All)]

if has_permission(user_john, "eat", apple_resource):
    print "Yum!"
```

The other function provided is ```list_permissions(user, resource)``` this will return a dict of all available permissions and a boolean value if the permission is granted or denied:

```python
from fastapi_permissions import list_permissions, Allow, All

user_john.principals == ["role:owner"]
apple_resource.__acl__ == [(Allow, "role:owner", All)]

print(list_permissions(user_john, apple_resouce))
{"permissions:*": True}
```

How it works
============

The main work is done in the ```has_permissions()``` function, but the most interesting ones (at least for me) are the ```configure_permissions()``` and ```permission_dependency_factory()``` functions. 

Wait. I didn't tell you about the latter one? Ok,

The ```permission()``` thingy used in the path operation definition before is actually the ```permission_dependency_factory()``` mentioned before. The ```configure_permissions()``` function just provisiones it with some default values using ```functools.partial```. This reduces the function signature from  ```permission_dependency_factory(permission, resource, current_user_func, grant_class, permission_exception)``` down to ```partial_function(permission, resource)```.

The ```permission_dependency_factory``` returns another function with the signature ```permission_dependency(Depends(resource), Depends(current_user_func))```. This is the acutal signature, that ```Depends()``` uses in the path operation definition to search and inject the dependencies. The rest is just some closure magic ;-).

Dev & Test virtual environment
------------------------------

Testing and development should be done with a virtual environment.

```
$ git clone https://github.com/holgi/fastapi-permissions.git
$ cd fastapi-permissions
$ python3 -m venv .venv --prompt permissions
$ source .venv/bin/activate
(permissions) $ pip install -U pip
```

Development requires flit to be installed:

```
(permissions) $ pip install flit
(permissions) $ flit install --pth-file
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




[FastApi]: https://fastapi.tiangolo.com/	" "
[dependency]: https://fastapi.tiangolo.com/tutorial/dependencies/first-steps/
[pyramid]: https://trypyramid.com
[pyramid_security]: https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/security.html
