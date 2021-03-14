# PyHP-Interpreter ![Tests](https://github.com/Deric-W/PyHP/workflows/Tests/badge.svg)  [![codecov](https://codecov.io/gh/Deric-W/PyHP/branch/master/graph/badge.svg?token=SA72E6KGXT)](https://codecov.io/gh/Deric-W/PyHP) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

PyHP is a package that allows you to embed Python code like PHP code into HTML and other text files.
A script is called either by the configuration of the web server or a shebang and communicates with the web server via CGI.

## Features:

  - Parser for embedding python Code in HTML
  - a bunch of PHP features implemented in python
  - modular structure to allow the use of features outside of the interpreter
  - automatic code alignment for improved readability
  - caching
  
## How it works:

 - Python code is contained within the `<?pyhp` and `?>` tags (like PHP)
 - the program is called like a interpreter, with a name as cli parameter
 - if no name is given, the program is reading from stdin, else it is using the name to load code from the backend configured in pyhp.toml
 - python code is allowed to have a starting indentation for better readability inside (for example) HTML files
 - the following PHP features are available as methods of the `PyHP` class (available from the outside in pyhp.libpyhp):
     - `$_SERVER` as `SERVER`
     - `$_REQUEST` as `REQUEST`
     - `$_GET` as `GET`
     - `$_POST` as `POST`
     - `$_COOKIE` as `COOKIE`
     - `http_response_code`
     - `header`
     - `headers_list`
     - `header_remove`
     - `headers_sent`
     - `header_register_callback`
     - `setcookie` with an additional `samesite` keyword argument
     - `setrawcookie` also with an additional `samesite` keyword argument
     - `register_shutdown_function`

  ## Config file

  - is valid toml
  - is looked for in these locations (no merging takes place, the first file wins):
    - the path given by the `-c` or `--config` cli argument
    - the path pointed to by the `PYHPCONFIG` environment variable
    - `~/.config/pyhp.toml`
    - `/etc/pyhp.toml`
  - raises a `RuntimeError` if not found
  
  ## Backends

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

  ### Debian package
  1. build the *pyhp-core* python package with `python3 setup.py bdist_wheel`
  2. go to the *debian* directory and execute `./build_deb.sh`
  3. enter a package version, the path of the *pyhp-core* wheel and the pip command you wish to use
  4. Done! You can now install the debian package with `sudo dpkg -i pyhp_<package version>_all.deb`

  ### Manually
  1. install the *pyhp-core* python package
  2. copy *pyhp.toml* to on of the config file locations
  3. Done! You can now use the `pyhp` command

