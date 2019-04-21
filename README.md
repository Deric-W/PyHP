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
