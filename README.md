# PyHP-Interpreter

This repository includes a script that allows you to embed Python code like PHP code into HTML.
The script is called either by the configuration of the web server or a shebang and communicates with the web server via CGI.

Features that are ready for testing:
  - Parser for embedding python Code in HTML
  - Encapsulation of the variables and functions of the interpreter in a separate class (to prevent accidental overwriting)
  - PHP like header function
  - PHP like REQUEST array (Dictionary)
  - PHP like SERVER array (Dictionary)
  
 Features that are currently being worked on:
  - Guide for installation
  - Documentation
  - improved parser and caching
  - PHP like htmlspecialchars function
  
## How it works:
 - Python code is contained within the <?pyhp and ?> tags (like PHP)
 - the Script is called like a interpreter, with the filepath as cli parameter
 - if no filepath is given, the script is reading from stdin
 - if "-c" is given, the file will be processed an cached in /etc/pyhp/relative/to/document root/filename.cache
   (the file is also loaded or renewed with this option)
 - python code can be away from the left site of the file for better optics --> Test4.pyhp
 - the following PHP features are available:
  - `$_REQUEST` as pyhp.REQUEST
  - `$_SERVER` as pyhp.SERVER
  - http_response_code as pyhp.http_response_code
  - headers_list as pyhp.headers_list
  - header as pyhp.header
  - header_remove as pyhp.header_remove
  - headers_sent as pyhp.headers_sent
  - automatic sending of headers with fallback: "Content-Type: text/html"
