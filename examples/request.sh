#!/bin/sh -e
# script for testing the request handling

cd request
export QUERY_STRING='test0=Hello&Test1=World%21&Test2=&Test3&&test0=World!'
export HTTP_COOKIE='test0=Hello ; Test1 = World%21 = Hello; Test2 = ;Test3;;test0=World!; ;'
pyhp methods.pyhp|diff methods.output -
pyhp request-order.pyhp --config request-order.conf|diff request-order.output -
cd ..
