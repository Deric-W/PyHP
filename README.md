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
     - `$_SERVER` as `SERVER`
     - `$_REQUEST` as `REQUEST`
     - `$_GET` as `GET`
     - `$_POST` as `POST`
     - `$_COOKIE` as `COOKIE`
     - `$_FILES` as `FILES`
     - `http_response_code`
     - `header`
     - `headers_list`
     - `header_remove`
     - `headers_sent`
     - `header_register_callback` with an additional `replace` keyword argument to register multiple callbacks
     - `setcookie` with an additional `samesite` keyword argument
     - `setrawcookie` also with an additional `samesite` keyword argument

  ### Config file

  - is valid toml
  - is looked for in these locations (no merging takes place, the first file wins):
    - the path given by the `-c` or `--config` cli argument
    - the path pointed to by the `PYHPCONFIG` environment variable
    - `~/.config/pyhp.toml`
    - `/etc/pyhp.toml`
  - raises a `RuntimeError` if not found
  
  ### Backends

  - implement code retrieval or decorate other backends to add i.a. caching
  - act as containers for CodeSources
  - form a hierarchy configured in pyhp.toml
  - are contained inside `pyhp.backends`
   
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

  - Optional: check if the recommended packages `python3-toml` and `python3-werkzeug` are installed to use the CLI commands 

  ### Manually
  1. install the *pyhp-core* python package
  2. set the `PYHPCONFIG` environ variable or copy *pyhp.toml* to one of the config file locations
  3. Done! You can now use the `pyhp-*` commands

