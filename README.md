# PyHP-Interpreter ![Tests](https://github.com/Deric-W/PyHP/workflows/Tests/badge.svg)  [![codecov](https://codecov.io/gh/Deric-W/PyHP/branch/master/graph/badge.svg?token=SA72E6KGXT)](https://codecov.io/gh/Deric-W/PyHP) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

The PyHP Interpreter is a package that allows you to embed Python code like PHP code into HTML and other text files.
The script is called either by the configuration of the web server or a shebang and communicates with the web server via CGI.

## Features:

  - Parser for embedding python Code in HTML
  - a bunch of PHP features implemented in python
  - modular structure to allow the use of features outside of the interpreter
  - automatic code alignment for improved readability
  - caching
  
## How it works:

 - Python code is contained within the `<?pyhp` and `?>` tags (like PHP)
 - the program is called like a interpreter, with the filepath as cli parameter
 - if no filepath is given, the program is reading from stdin
 - if the `-c` or `--caching` is given, the cache will be enabled and the file will additionally be preprocessed if needed 
   and cached in cache_path/absolute/path/of/filename.cache
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
     
  
  ## Cache Handlers
  
 - are responsible for saving/loading/renewing caches
 - are python scripts with the following contents:
 - the `Handler` class, wich takes the cache path, absolute file path and `caching` section of the config file as  
   initialization parameters and provides the following methods:
     - `is_available`, wich returns a boolean indicating if the handler can be used
     - `is_outdated`, wich returns a boolean indicating if the cache needs to be renewed
     - `save`, wich takes an code object as an argument and saves it in the cache
     - `load`, wich loads an code object from the cache
     - `close`, wich does cleanup tasks and gets called when used as a context manager
  - note that code objects have to support the pickle protocol
  - examples are available in the *cache_handlers* directory
   
  ## Installation
  
  This section shows you how to install PyHP on your computer.
  If you want to use *pyhp* scripts on your website by CGI you have to additionally enable CGI in your webserver.
  
  ### Just as python package
  1. build the *pyhp-core* python package with `python3 setup.py bdist_wheel`
  2. Done! You can now install the wheel contained in the *dist* directory with pip
  
  ### As application
  If you just installed the python package, then you have to provide `--config` with every call of `python3 -m pyhp`
  and can't use the caching feature.
  To stop this, you can build a debian package or install PyHP manually.
  
  #### Debian package
  1. build the *pyhp-core* python package with `python3 setup.py bdist_wheel`
  2. go to the *debian* directory and execute `./build_deb.sh`
  3. enter a package version, the path of the *pyhp-core* wheel and the pip command you wish to use
  4. Done! You can now install the debian package with `sudo dpkg -i pyhp_<package version>_all.deb`
  
  #### Manually
  1. install the *pyhp-core* python package
  2. copy *pyhp.conf* to */etc*
  3. copy *cache_handlers* to */lib/pyhp/*
  4. copy *debian/pyhp* to a directoy in your PATH
  5. Done! You can now use the `pyhp` command
  
