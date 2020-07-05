#!/usr/bin/env bash

SCRIPTS_DIR=$1
LOCAL_IN_PATH="./"

########################################################################## PARSER

PARSER_TASK_INTERPRET=php7.3
PARSER_TASK_NAME=parse
PARSER_TASK_EXTENSION=php
PARSER_TASK_TESTS_DIR=supplementary-tests/parse-only/
PARSER_TASK_TESTS_LOG_DIR=$2
PARSER_TASK=$SCRIPTS_DIR/$PARSER_TASK_NAME

for TEST_NAME in read_test simple_tag write_test; do
    $PARSER_TASK_INTERPRET $PARSER_TASK.$PARSER_TASK_EXTENSION < ${LOCAL_IN_PATH}$PARSER_TASK_TESTS_DIR$TEST_NAME.src > ${PARSER_TASK_TESTS_LOG_DIR}$TEST_NAME.out
    echo -n $? > ${PARSER_TASK_TESTS_LOG_DIR}$TEST_NAME.rc
done

########################################################################## INTERPRET

INTERPRET_TASK_INTERPRET=python3.6
INTERPRET_TASK_NAME=interpret
INTERPRET_TASK_EXTENSION=py
INTERPRET_TASK_TESTS_DIR=supplementary-tests/int-only/
INTERPRET_TASK_TESTS_LOG_DIR=$3
INTERPRET_TASK=$SCRIPTS_DIR/$INTERPRET_TASK_NAME

for TEST_NAME in stack_test write_test; do
    $INTERPRET_TASK_INTERPRET $INTERPRET_TASK.$INTERPRET_TASK_EXTENSION < ${LOCAL_IN_PATH}$INTERPRET_TASK_TESTS_DIR$TEST_NAME.src --input ${LOCAL_IN_PATH}$INTERPRET_TASK_TESTS_DIR$TEST_NAME.in > ${INTERPRET_TASK_TESTS_LOG_DIR}$TEST_NAME.out 2> ${INTERPRET_TASK_TESTS_LOG_DIR}$TEST_NAME.err
    echo -n $? > ${INTERPRET_TASK_TESTS_LOG_DIR}$TEST_NAME.rc
done
