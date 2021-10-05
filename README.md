# PyHP-Interpreter [![Tests](https://github.com/Deric-W/PyHP/actions/workflows/Tests.yaml/badge.svg)](https://github.com/Deric-W/PyHP/actions/workflows/Tests.yaml)  [![codecov](https://codecov.io/gh/Deric-W/PyHP/branch/master/graph/badge.svg?token=SA72E6KGXT)](https://codecov.io/gh/Deric-W/PyHP) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

PyHP is a package that allows you to embed Python code like PHP code into HTML and other text files.
A script is called either by the configuration of the web server or a shebang and communicates with the web server via WSGI.

## Features:

  - Parser for embedding python Code in HTML
  - a bunch of PHP features implemented in python
  - modular structure to allow the use of features outside of the interpreter
  - automatic code alignment for improved readability
  - caching
  
## How it works:

 ### Syntax
 - like PHP, Python code is contained within the `<?pyhp` and `?>` tags
 - code sections are allowed to have a starting indentation for better readability inside (for example) HTML files
 - unlike PHP, each code section of code must have a valid syntax of its own
   - if-Statements or loops can not span multiple code sections

 ### Runtime
 - module level constants are set and allow for source introspection if the backend supports it
 - `exit` and [`sys.exit`](https://docs.python.org/3/library/sys.html#sys.exit) terminate the script, not the whole server
 - [`atexit`](https://docs.python.org/3/library/atexit.html) registered functions dont get called until server shutdown in WSGI mode
 - since try statements can't span multiple code sections cleanup actions should be executed by [`register_shutdown_function`](#php-interface)

 ### Usage
 - can be used for
  - CLI scripts with the `pyhp-cli` command
  - CGI scripts by using the `pyhp-cgi` command
  - WSGI servers by using the `pyhp.wsgi.apps` submodule
 - if no name is given, the program is reading from stdin, else it is using the name to load code from the configured backend

 ### Apps
 - execute code and capture its output
 - provide the code with an interface
 - are available for single and multi-threaded environments
 - can be constructed by factories contained in the `pyhp.wsgi.util` submodule

 ### Interfaces
 - act as an interface between the WSGI gateway and the script
 - are available as thin WSGI wrappers or PHP-style interfaces

 ### PHP Interface
 - the following PHP features are available:
     - [`$_SERVER`](https://www.php.net/manual/en/reserved.variables.server.php) as `SERVER`
     - [`$_REQUEST`](https://www.php.net/manual/en/reserved.variables.request.php) as `REQUEST`
     - [`$_GET`](https://www.php.net/manual/en/reserved.variables.get.php) as `GET`
     - [`$_POST`](https://www.php.net/manual/en/reserved.variables.post.php) as `POST`
     - [`$_COOKIE`](https://www.php.net/manual/en/reserved.variables.cookies.php) as `COOKIE`
     - [`$_FILES`](https://www.php.net/manual/en/reserved.variables.files.php) as `FILES`
     - [`http_response_code`](https://www.php.net/manual/en/function.http-response-code)
     - [`header`](https://www.php.net/manual/en/function.header.php)
     - [`headers_list`](https://www.php.net/manual/en/function.headers-list.php)
     - [`header_remove`](https://www.php.net/manual/en/function.header-remove.php)
     - [`headers_sent`](https://www.php.net/manual/en/function.headers-sent.php)
     - [`header_register_callback`](https://www.php.net/manual/en/function.header-register-callback.php) with an additional `replace` keyword argument to register multiple callbacks
     - [`setcookie`](https://www.php.net/manual/en/function.setcookie.php) with an additional `samesite` keyword argument
     - [`setrawcookie`](https://www.php.net/manual/en/function.setrawcookie.php) also with an additional `samesite` keyword argument
     - [`register_shutdown_function`](https://www.php.net/manual/en/function.register-shutdown-function) with reversed callback execution order (LIFO)
     - [`opcache_compile_file`](https://www.php.net/manual/en/function.opcache-compile-file) which raises Exceptions instead of returning `False` when compilation fails
     - [`opcache_invalidate`](https://www.php.net/manual/en/function.opcache-invalidate.php)
     - [`opcache_is_script_cached`](https://www.php.net/manual/en/function.opcache-is-script-cached.php)
     - [`opcache_reset`](https://www.php.net/manual/en/function.opcache-reset.php)

  ### Config file

  - is valid [toml](https://toml.io)
  - is looked for in these locations (no merging takes place, the first file wins):
    - the path given by the `-c` or `--config` cli argument
    - the path pointed to by the `PYHPCONFIG` environment variable
    - `~/.config/pyhp.toml`
    - `/etc/pyhp.toml`
  - raises a [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError) if not found
  
  ### Backends

  - implement code retrieval or decorate other backends to add i.a. caching
  - act as containers for CodeSources
  - form a hierarchy configured in pyhp.toml
  - are contained inside `pyhp.backends`
  - can be interacted with via the `pyhp-backend` or `python3 -m pyhp.backends` cli commands
   
  ## Installation
  
  This section shows you how to install PyHP on your computer.
  If you want to use *pyhp* scripts on your website by CGI you have to additionally enable CGI in your webserver.
  
  ### Just as python package
  1. build the *pyhp-core* python package with `python3 setup.py bdist_wheel`
  2. Done! You can now install the wheel contained in the *dist* directory with pip
      
  - Optional: set the `PYHPCONFIG` environ variable or copy *pyhp.toml* to one of the config file locations to use the CLI commands

  ### Debian package
  1. execute `debian/build_deb.sh` in the root directory of the project.
  2. Done! You can now install the debian package with `sudo dpkg -i python3-pyhp-core_{version}-1_all.deb`

  - Optional: check if the recommended packages [`python3-toml`](https://packages.debian.org/search?keywords=python3-toml) and [`python3-werkzeug`](https://packages.debian.org/search?keywords=python3-werkzeug) are installed to use the CLI commands
  - Important: `pyhp-backend clear` will be executed on uninstall or upgrade if the backend is a cache, remember this when using paths containing `~` for the file cache

  ### Manually
  1. install the *pyhp-core* python package
  2. set the `PYHPCONFIG` environ variable or copy *pyhp.toml* to one of the config file locations
  3. Done! You can now use the `pyhp-*` commands

  ## WSGI Example

  ### Manually

  ```python
      import sys
      import re
      import tempfile
      from wsgiref.simple_server import make_server
      from pyhp.compiler import parsers, util, generic
      from pyhp.backends.files import Directory
      from pyhp.wsgi.apps import ConcurrentWSGIApp
      from pyhp.wsgi.proxys import LocalStackProxy
      from pyhp.wsgi.interfaces.php import PHPWSGIInterfaceFactory
      from pyhp.wsgi.interfaces.phputils import UploadStreamFactory


      compiler = util.Compiler(
          parsers.RegexParser(
              re.compile(r"<\?pyhp\s"),
              re.compile(r"\s\?>")
          ),
          util.Dedenter(
              generic.GenericCodeBuilder(-1)
          )
      )

      interface_factory = PHPWSGIInterfaceFactory(
          200,
          [("Content-type", "text/html; charset=\"UTF-8\"")],
          None,
          ("GET", "POST", "COOKIE"),
          8000000,
          UploadStreamFactory(
              tempfile.gettempdir(),
              20
          )
      )

      sys.stdout = proxy = LocalStackProxy(sys.stdout)

      with Directory(".", compiler) as backend:
          with ConcurrentWSGIApp("tests/embedding/syntax.pyhp", backend, proxy, interface_factory) as app:
              with make_server("", 8000, app) as httpd:
                  httpd.serve_forever()

  ```

  ### From a config file

  ```python
    from wsgiref.simple_server import make_server
    import toml
    from pyhp.wsgi.util import ConcurrentWSGIAppFactory


    config = toml.load("pyhp.toml")

    with ConcurrentWSGIAppFactory.from_config(config) as factory:
        with factory.app("tests/embedding/syntax.pyhp") as app:
            with make_server("", 8000, app) as httpd:
                httpd.serve_forever()
  ```
