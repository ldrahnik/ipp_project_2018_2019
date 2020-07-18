#!/usr/bin/env bash

SCRIPTS_DIR=$1

PARSER_TASK_TESTS_DIR=$2
PARSER_TASK_TESTS_LOG_DIR=$3

INTERPRET_TASK_TESTS_DIR=$4
INTERPRET_TASK_TESTS_LOG_DIR=$5

BOTH_TASK_TESTS_DIR=$6
BOTH_TASK_TESTS_LOG_DIR=$7

########################################################################## SCRIPTS

# script parse
PARSER_TASK_INTERPRET=php7.3
PARSER_TASK_NAME=parse
PARSER_TASK_EXTENSION=php
PARSER_TASK_FULLNAME="$SCRIPTS_DIR/$PARSER_TASK_NAME.$PARSER_TASK_EXTENSION"
PARSER_TASK="$PARSER_TASK_INTERPRET $SCRIPTS_DIR/$PARSER_TASK_NAME.$PARSER_TASK_EXTENSION"

# script interpret
INTERPRET_TASK_INTERPRET=python3.6
INTERPRET_TASK_NAME=interpret
INTERPRET_TASK_EXTENSION=py
INTERPRET_TASK_FULLNAME="$SCRIPTS_DIR/$INTERPRET_TASK_NAME.$INTERPRET_TASK_EXTENSION"
INTERPRET_TASK="$INTERPRET_TASK_INTERPRET $SCRIPTS_DIR/$INTERPRET_TASK_NAME.$INTERPRET_TASK_EXTENSION"

# script tester
TESTER_TASK_INTERPRET=php7.3
TESTER_TASK_NAME=test
TESTER_TASK_EXTENSION=php
TESTER_TASK_FULLNAME="$SCRIPTS_DIR/$TESTER_TASK_NAME.$TESTER_TASK_EXTENSION"
TESTER_TASK="$TESTER_TASK_INTERPRET $SCRIPTS_DIR/$TESTER_TASK_NAME.$TESTER_TASK_EXTENSION"

########################################################################## TEST

function tester() {

    # function args
    TESTS_DIR=$1
    LOG_DIR=$2
    TEST_NAME=$3

    # follow specific args for test script
    shift 3

    TMP_FILE=$( mktemp /tmp/ipp_tester_$TEST_NAME.XXXXXX)
    echo -e "$TESTS_DIR$TEST_NAME.src\n" > $TMP_FILE
    $TESTER_TASK > "$LOG_DIR$TEST_NAME.html" --testlist $TMP_FILE "$@"
    echo -n $? > "$LOG_DIR$TEST_NAME.html.rc"
    rm $TMP_FILE
}

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

    $PARSER_TASK < $TESTS_DIR$TEST_NAME.src > $OUTPUT_FILE
    echo -n $? > $LOG_DIR$TEST_NAME.rc
}

for TEST_FILE_NAME in $(find $PARSER_TASK_TESTS_DIR -maxdepth 1 -type f -name "*.src" -printf "%f\n"); do
    TEST_NAME=${TEST_FILE_NAME%.src}
    parse $PARSER_TASK_TESTS_DIR $PARSER_TASK_TESTS_LOG_DIR $TEST_NAME
    tester $PARSER_TASK_TESTS_DIR $PARSER_TASK_TESTS_LOG_DIR $TEST_NAME --parse-only --parse-script $PARSER_TASK_FULLNAME
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

    $INTERPRET_TASK < $SOURCE_FILE --input $TESTS_DIR$TEST_NAME.in > $LOG_DIR$TEST_NAME.out 2> $LOG_DIR$TEST_NAME.err
    echo -n $? > $LOG_DIR$TEST_NAME.rc
}

for TEST_FILE_NAME in $(find $INTERPRET_TASK_TESTS_DIR -maxdepth 1 -type f -name "*.src" -printf "%f\n"); do
    TEST_NAME=${TEST_FILE_NAME%.src}
    interpret $INTERPRET_TASK_TESTS_DIR $INTERPRET_TASK_TESTS_LOG_DIR $TEST_NAME
    tester $INTERPRET_TASK_TESTS_DIR $INTERPRET_TASK_TESTS_LOG_DIR $TEST_NAME --int-only --int-script $INTERPRET_TASK_FULLNAME
done

########################################################################## BOTH

function both() {

    # function args
    TESTS_DIR=$1
    LOG_DIR=$2
    TEST_NAME=$3

    # parser output is interpret input
    PIPE_FILE=$LOG_DIR$TEST_NAME.xml

    parse $TESTS_DIR $LOG_DIR $TEST_NAME $PIPE_FILE $PIPE_FILE
    interpret $TESTS_DIR $LOG_DIR $TEST_NAME $PIPE_FILE
    tester $TESTS_DIR $LOG_DIR $TEST_NAME --int-script $INTERPRET_TASK_FULLNAME --parse-script $PARSER_SCRIPT_FULLNAME
}

for TEST_FILE_NAME in $(find $BOTH_TASK_TESTS_DIR -maxdepth 1 -type f -name "*.xml" -printf "%f\n"); do
    TEST_NAME=${TEST_FILE_NAME%.xml}
    both $BOTH_TASK_TESTS_DIR $BOTH_TASK_TESTS_LOG_DIR $TEST_NAME
done
