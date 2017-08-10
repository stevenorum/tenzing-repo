#!/bin/bash

TEMP_DIR='tenzing-zipdir'

TEMPLATE="sunyata/prod.json"

if [ -e "$1" ] ; then
    TEMPLATE="$1"
fi

bundle() {
    mkdir $TEMP_DIR
    echo -e '[install]\nprefix=' > ~/.pydistutils.cfg
    pip3 install jinja2 -t $TEMP_DIR/
    pip3 install setuptools -t $TEMP_DIR/
    rm ~/.pydistutils.cfg
    cp -R tenzing/* $TEMP_DIR/
    cp -R ../junko/junko $TEMP_DIR/
}

cleanup() {
    rm -rf $TEMP_DIR
}

cleanup
bundle
BASE_CMD="sunyata -v --template $TEMPLATE"
$BASE_CMD --create || $BASE_CMD --deploy
cleanup
