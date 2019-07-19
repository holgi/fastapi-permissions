# fastapi-permissions

## Row Level Security for FastAPI

This is just a quick scribble of an idea of a row level permission module for
[FastApi][]


To test this you need to install the following packages:

```
pip install "fastapi[all]"
pip install pyjwt
pip install "passlib[bcrypt]"

```

You can run the test-app with ```uvicorn main:app --reload``` and visit
<http://127.0.0.1:8000/docs>

There are two users: "johndoe" and "alice", both have the password "secret".

[FastApi]: https://fastapi.tiangolo.com/
