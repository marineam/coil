#!/bin/bash

epydoc --text coil | sed -e $'s/\b.//g' | grep -A 1000 ^DESCRIPTION \
    | grep -B 1000 ^FUNCTIONS | egrep -v '^\w' | sed -e 's/^    //'
