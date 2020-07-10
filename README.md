# PyHP-Interpreter  [![Build Status](https://travis-ci.org/Deric-W/PyHP.svg?branch=master)](https://travis-ci.org/Deric-W/PyHP)

The PyHP Interpreter is a package that allows you to embed Python code like PHP code into HTML and other text files.
The script is called either by the configuration of the web server or a shebang and communicates with the web server via CGI.

## Features:

  - Parser for embedding python Code in HTML
  - a bunch of PHP features implemented in python
  - modular structure to allow the use of features outside of the interpreter
  - automatic code alignment for improved readability inside HTML files
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
     - `opcache_is_script_cached` as `cache_is_script_cached` (raises NotImplementedError if cache is disabled)
     - `opcache_invalidate` as `cache_invalidate` (raises NotImplementedError instead of returnig False if cache is disabled)
     - `opcache_reset` as `cache_reset` (raises NotImplementedError instead of returnig False if cache is disabled)
     - `register_shutdown_function`
     
  
  ## Cache Handlers
  
 - are responsible for saving, loading and removing caches
 - are python scripts with a `Handler` class, which takes as parameters `location`, `max_size` and `ttl`, is thread safe and contains:
     - a `renew_exceptions` attribute, which is a tuple containing exceptions to be raised by `load` if the cache entry is outdated
     - a `is_outdated(file_path)` method, which returns a bool indicating if the cache entry for the file is outdated or does not exist
     - a `load(file_path)` method, which loads the cache entry for the file or raises a exception from `renew_exceptions` if the cache entry is outdated
     - a `save(file_path, sections)` method, which saves the code sections (a tuple) in the cache entry for the file
     - a `remove(file_path)` method, which removes the cache entry from the cache
     - a `reset()` method, which removes the entire cache
     - a `shutdown()` method, which does cleanup tasks
 - note that the tuple may contain code objects which can't be pickled
 - handlers available in the *cache_handlers* directory:
     - `files_mtime.py`, which stores the cache entries in seperate files and detects outdated entries with their modification time
     - `memory_mtime.py`, which stores the cache entries in memory and detects outdated entries with their modification time (useless when using CGI)


  ## Problems

  Because code sections inside pyhp files are compiled one by one the exceptions raised by them think they startet at line 1.
  This causes exceptions to have line numbers relative to the start of their code section and not display the code that caused them.
  In Python 3.8 code objects got a `replace` method which PyHP can use to set the line numbers correctly.
  While Python 3.7 is the Python version found on most Linux systems i cant drop support for it.
  In the meantime, just ignore the code shown by exceptions and look at the correct line in the source file.

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
  3. enter a package name, the path of the *pyhp-core* wheel and the pip command you wish to use
  4. Done! You can now install the debian package with `sudo dpkg -i <package name>.deb`
  
  #### Manually
  1. install the *pyhp-core* python package
  2. copy *pyhp.conf* to */etc*
  3. copy *cache_handlers* to */usr/lib/pyhp/*
  4. copy *debian/pyhp* to a directoy in your PATH
  5. Done! You can now use the `pyhp` command
