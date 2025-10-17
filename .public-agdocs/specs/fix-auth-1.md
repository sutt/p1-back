I'm getting the following err, how to fix?

Traceback (most recent call last):
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/handlers/bcrypt.py", line 620, in _load_backend_mixin
    version = _bcrypt.__about__.__version__
              ^^^^^^^^^^^^^^^^^
AttributeError: module 'bcrypt' has no attribute '__about__'
INFO:     127.0.0.1:60662 - "POST /api/signup HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/uvicorn/protocols/http/httptools_impl.py", line 409, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/fastapi/applications.py", line 1133, in __call__
    await super().__call__(scope, receive, send)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/starlette/applications.py", line 113, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/starlette/middleware/cors.py", line 93, in __call__
    await self.simple_response(scope, receive, send, request_headers=headers)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/starlette/middleware/cors.py", line 144, in simple_response
    await self.app(scope, receive, send)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/starlette/routing.py", line 716, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/starlette/routing.py", line 736, in app
    await route.handle(scope, receive, send)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/starlette/routing.py", line 290, in handle
    await self.app(scope, receive, send)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/fastapi/routing.py", line 123, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/fastapi/routing.py", line 109, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/fastapi/routing.py", line 389, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/fastapi/routing.py", line 288, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/main.py", line 117, in signup
    hashed_password = auth.get_password_hash(user.password)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/auth.py", line 56, in get_password_hash
    return pwd_context.hash(password)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/context.py", line 2258, in hash
    return record.hash(secret, **kwds)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/utils/handlers.py", line 779, in hash
    self.checksum = self._calc_checksum(secret)
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/handlers/bcrypt.py", line 591, in _calc_checksum
    self._stub_requires_backend()
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/utils/handlers.py", line 2254, in _stub_requires_backend
    cls.set_backend()
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/utils/handlers.py", line 2156, in set_backend
    return owner.set_backend(name, dryrun=dryrun)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/utils/handlers.py", line 2163, in set_backend
    return cls.set_backend(name, dryrun=dryrun)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/utils/handlers.py", line 2188, in set_backend
    cls._set_backend(name, dryrun)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/utils/handlers.py", line 2311, in _set_backend
    super(SubclassBackendMixin, cls)._set_backend(name, dryrun)
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/utils/handlers.py", line 2224, in _set_backend
    ok = loader(**kwds)
         ^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/handlers/bcrypt.py", line 626, in _load_backend_mixin
    return mixin_cls._finalize_backend_mixin(name, dryrun)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/handlers/bcrypt.py", line 421, in _finalize_backend_mixin
    if detect_wrap_bug(IDENT_2A):
       ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/handlers/bcrypt.py", line 380, in detect_wrap_bug
    if verify(secret, bug_hash):
       ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/utils/handlers.py", line 792, in verify
    return consteq(self._calc_checksum(secret), chk)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/gauntlet/pkgs/p1-back/.venv/lib/python3.12/site-packages/passlib/handlers/bcrypt.py", line 655, in _calc_checksum
    hash = _bcrypt.hashpw(secret, config)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ValueError: password cannot be longer than 72 bytes, truncate manually if necessary (e.g. my_password[:72])