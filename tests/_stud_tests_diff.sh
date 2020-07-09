#!/usr/bin/env bash

# Name:	Lukáš Drahník
# Project: Zadání projektu z předmětu IPP 2018/2019
# Date:	4.7.2020
# Email: <xdrahn00@stud.fit.vutbr.cz>, <ldrahnik@gmail.com>

# jexamxml.jar
JEXAMXML_JAR_FILE=$1
# jexamxml tmp file
JEXAMXML_TMP_FILE=$2
# options
JEXAMXML_OPTIONS_FILE=$3

# Složky referenčního výstupu a výstupu k porovnání.
PARSE_LOG_DIR=$4
PARSE_REF_DIR=$5

INT_LOG_DIR=$6
INT_REF_DIR=$7

BOTH_LOG_DIR=$8
BOTH_REF_DIR=$9

########################################################################## PARSER

function parse() {
    LOG_DIR=$1
    REF_LOG_DIR=$2
    TEST_NAME=$3
    if [ -z "$4" ]
    then
        EXTENSION_OUTPUT_FILE=out
    else
        EXTENSION_OUTPUT_FILE=$4
    fi

    # Zkontrolujeme návratovou hodnotu.
    if diff "$LOG_DIR$TEST_NAME.rc" "$REF_LOG_DIR$TEST_NAME.rc"; then

        # Pokud je návratová hodnota "0", zkontrolujeme i výstup.
        if [[ $(head -n 1 "$REF_LOG_DIR$TEST_NAME.rc") == "0" ]]; then

            # Porovnání výstupu s referenčním provedeme pomocí knihovny JEXAMXML.
            $(java -jar $JEXAMXML_JAR_FILE "$LOG_DIR$TEST_NAME.$EXTENSION_OUTPUT_FILE" "$REF_LOG_DIR$TEST_NAME.$EXTENSION_OUTPUT_FILE" $JEXAMXML_TMP_FILE $JEXAMXML_OPTIONS_FILE > /dev/null);
            if [ $? -eq 0 ]; then
                echo "*******TEST $TEST_NAME PASSED";
            # Podrobnější výpis co je rozdílné v případě neshody je uložen do souboru $JEXAMXML_TMP_FILE, který se zobrazí.
            else
                cat $JEXAMXML_TMP_FILE
                echo "TEST $TEST_NAME FAILED";
            fi
        # Pokud návratová hodnota není "0", program byl ukončen předčasně a výstup nebyl generován. Test proběhl úspěšně.
        else
            echo "*******TEST $TEST_NAME PASSED";
        fi
    else
        echo "TEST $TEST_NAME FAILED";
    fi
}

echo "############################### PARSE"

for TEST_NAME in read_test simple_tag write_test; do
    parse $PARSE_LOG_DIR $PARSE_REF_DIR $TEST_NAME
done

########################################################################## INTERPRET

function interpret() {
    LOG_DIR=$1
    REF_LOG_DIR=$2
    TEST_NAME=$3

    # Zkontrolujeme návratovou hodnotu.
    if diff "$LOG_DIR$TEST_NAME.rc" "$REF_LOG_DIR$TEST_NAME.rc"; then

        # Pokud je návratová hodnota "0", zkontrolujeme i výstup.
        if [[ $(head -n 1 "$REF_LOG_DIR$TEST_NAME.rc") == "0" ]]; then

            # Porovnání výstupu s referenčním provedeme pomocí diff.
            if diff "$LOG_DIR$TEST_NAME.out" "$REF_LOG_DIR$TEST_NAME.out"; then
                echo "*******TEST $TEST_NAME PASSED";
            else
                echo "TEST $TEST_NAME FAILED";
            fi
        # Pokud návratová hodnota není "0", program byl ukončen předčasně a výstup nebyl generován. Test proběhl úspěšně.
        else
            echo "*******TEST $TEST_NAME PASSED";
        fi
    else
        echo "TEST $TEST_NAME FAILED";
    fi

}

########################################################################## BOTH

function both() {
    LOG_DIR=$1
    REF_LOG_DIR=$2
    TEST_NAME=$3

     # parser output is interpret input
    EXTENSION_OUTPUT_FILE=xml

    echo "############### PARSER"

    parse $BOTH_LOG_DIR $BOTH_REF_DIR $TEST_NAME $EXTENSION_OUTPUT_FILE

    echo "############### INTERPRET"

    interpret $BOTH_LOG_DIR $BOTH_REF_DIR $TEST_NAME
}

echo "############################### INTERPRET"

for TEST_NAME in stack_test write_test; do
    interpret $INT_LOG_DIR $INT_REF_DIR $TEST_NAME
done

echo "############################### BOTH"

for TEST_NAME in error_string_out_of_range read_test simple_program float; do
    both $BOTH_LOG_DIR $BOTH_REF_DIR $TEST_NAME
done
