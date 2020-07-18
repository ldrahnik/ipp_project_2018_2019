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
PARSE_REF_DIR=$4
PARSE_LOG_DIR=$5

INT_REF_DIR=$6
INT_LOG_DIR=$7

BOTH_REF_DIR=$8
BOTH_LOG_DIR=$9

########################################################################## TESTER

function tester() {

    # Argumenty funkce.
    LOG_DIR=$1
    TEST_NAME=$2

    # Pokud je návratová hodnota "0", zkontrolujeme i výstup.
    if [[ $(head -n 1 "$LOG_DIR$TEST_NAME.html.rc") == "0" ]]; then

        # Porovnání výstupu s referenčním provedeme pomocí diff.
        if grep --quiet --word-regexp "Celková úspěšnost složek: 1/1" "$LOG_DIR$TEST_NAME.html"; then
            echo "*******TEST $TEST_NAME PASSED (TESTER)";
        else
            echo "TEST $TEST_NAME FAILED (TESTER)";
        fi
    else
        echo "TEST $TEST_NAME FAILED (TESTER)";
    fi
}

########################################################################## PARSER

function parse() {

    # Argumenty funkce.
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

for TEST_FILE_NAME in $(find $PARSE_REF_DIR -maxdepth 1 -type f -name "*.out" -printf "%f\n"); do
    TEST_NAME=${TEST_FILE_NAME%.out}
    parse $PARSE_LOG_DIR $PARSE_REF_DIR $TEST_NAME
    tester $PARSE_LOG_DIR $TEST_NAME
done

########################################################################## INTERPRET

function interpret() {

    # Argumenty funkce.
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

    echo "############### PARSER + INTERPRET"

    tester $LOG_DIR $TEST_NAME
}

echo "############################### INTERPRET"

for TEST_FILE_NAME in $(find $INT_REF_DIR -maxdepth 1 -type f -name "*.out" -printf "%f\n"); do
    TEST_NAME=${TEST_FILE_NAME%.out}
    interpret $INT_LOG_DIR $INT_REF_DIR $TEST_NAME
    tester $INT_LOG_DIR $TEST_NAME
done

echo "############################### BOTH"

for TEST_FILE_NAME in $(find $BOTH_REF_DIR -maxdepth 1 -type f -name "*.src" -printf "%f\n"); do
    TEST_NAME=${TEST_FILE_NAME%.src}
    both $BOTH_LOG_DIR $BOTH_REF_DIR $TEST_NAME
done
