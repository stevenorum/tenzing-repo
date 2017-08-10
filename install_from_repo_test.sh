#!/bin/bash

TEST_DIR='tenzing-testdir'

PIP_CONF="${HOME}/.pip/pip.conf"
PIP_CONF_TEMP="${HOME}/.pip/pip.conf.backup"

API_HOST="5g1m9emx29.execute-api.us-east-1.amazonaws.com"

USERNAME="ThisIsAUsername"
PASSWORD="ThisIsAPassword"

bundle() {
    mkdir $TEST_DIR
    mkdir -p ~/.pip
    echo -e '[install]\nprefix=' > ~/.pydistutils.cfg
    TEMP_LOCATION=""
    if [ -e "$PIP_CONF" ] ; then
        mv $PIP_CONF $PIP_CONF_TEMP
    fi
    echo "[global]" >> $PIP_CONF
    echo "; Extra index to private pypi dependencies" >> $PIP_CONF
    echo "extra-index-url = https://${USERNAME}:${PASSWORD}@${API_HOST}/prod/repo/" >> $PIP_CONF
    echo "trusted-host = $API_HOST" >> $PIP_CONF

    pip3 install boto3 -t $TEST_DIR/ -vvv
    pip3 install sunyata -t $TEST_DIR/ -vvv
    rm ~/.pydistutils.cfg
    rm $PIP_CONF
    if [ -e "$PIP_CONF_TEMP" ] ; then
        mv $PIP_CONF_TEMP $PIP_CONF
    fi
}

cleanup() {
    rm -rf $TEST_DIR
}

cleanup
bundle
#cleanup
