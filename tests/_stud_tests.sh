#!/usr/bin/env bash

SCRIPTS_DIR=$1

PARSER_TASK_TESTS_DIR=$2
PARSER_TASK_TESTS_LOG_DIR=$3

INTERPRET_TASK_TESTS_DIR=$4
INTERPRET_TASK_TESTS_LOG_DIR=$5

BOTH_TASK_TESTS_DIR=$6
BOTH_TASK_TESTS_LOG_DIR=$7

########################################################################## PARSER

function parse() {

    # function args
    TESTS_DIR=$1
    LOG_DIR=$2
    TEST_NAME=$3
    if [ -z "$4" ]
    then
        OUTPUT_FILE=$LOG_DIR$TEST_NAME.out
    else
        OUTPUT_FILE=$4
    fi

    # script parse
    PARSER_TASK_INTERPRET=php7.3
    PARSER_TASK_NAME=parse
    PARSER_TASK_EXTENSION=php
    PARSER_TASK=$SCRIPTS_DIR/$PARSER_TASK_NAME

    $PARSER_TASK_INTERPRET $PARSER_TASK.$PARSER_TASK_EXTENSION < $TESTS_DIR$TEST_NAME.src > $OUTPUT_FILE
    echo -n $? > $LOG_DIR$TEST_NAME.rc
}

for TEST_NAME in read_test simple_tag write_test; do
    parse $PARSER_TASK_TESTS_DIR $PARSER_TASK_TESTS_LOG_DIR $TEST_NAME
done

########################################################################## INTERPRET

function interpret() {

    # function args
    TESTS_DIR=$1
    LOG_DIR=$2
    TEST_NAME=$3
    if [ -z "$4" ]
    then
        SOURCE_FILE=$TESTS_DIR$TEST_NAME.src
    else
        SOURCE_FILE=$4
    fi

    # script interpret
    INTERPRET_TASK_INTERPRET=python3.6
    INTERPRET_TASK_NAME=interpret
    INTERPRET_TASK_EXTENSION=py
    INTERPRET_TASK=$SCRIPTS_DIR/$INTERPRET_TASK_NAME

    $INTERPRET_TASK_INTERPRET $INTERPRET_TASK.$INTERPRET_TASK_EXTENSION < $SOURCE_FILE --input $TESTS_DIR$TEST_NAME.in > $LOG_DIR$TEST_NAME.out 2> $LOG_DIR$TEST_NAME.err
    echo -n $? > $LOG_DIR$TEST_NAME.rc
}

for TEST_NAME in stack_test write_test; do
    interpret $INTERPRET_TASK_TESTS_DIR $INTERPRET_TASK_TESTS_LOG_DIR $TEST_NAME
done

########################################################################## BOTH

function both() {

    # function args
    TESTS_DIR=$1
    LOG_DIR=$2
    TEST_NAME=$3

    # parser output is interpret input
    PIPE_FILE=$LOG_DIR$TEST_NAME.xml

    parse $TESTS_DIR $LOG_DIR $TEST_NAME $PIPE_FILE
    interpret $TESTS_DIR $LOG_DIR $TEST_NAME $PIPE_FILE
}

for TEST_NAME in error_string_out_of_range read_test simple_program; do
    both $BOTH_TASK_TESTS_DIR $BOTH_TASK_TESTS_LOG_DIR $TEST_NAME
done
