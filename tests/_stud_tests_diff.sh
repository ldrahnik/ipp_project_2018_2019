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
PARSE_OUT_DIR=$4
PARSE_REF_OUT_DIR=$5

INT_OUT_DIR=$6
INT_REF_OUT_DIR=$7

########################################################################## PARSER

echo "############################### PARSE"

for TEST_NAME in read_test simple_tag write_test; do

    # Zkontrolujeme návratovou hodnotu.
    if diff "$PARSE_OUT_DIR/$TEST_NAME.rc" "$PARSE_REF_OUT_DIR/$TEST_NAME.rc" > /dev/null; then

        # Pokud návratová hodnota je "0", zkontrolujeme i výstup.
        if [[ $(head -n 1 "$PARSE_REF_OUT_DIR/$TEST_NAME.rc") == "0" ]]; then

            # Porovnání výstupu s referenčním provedeme pomocí knihovny JEXAMXML.
            eval $(java -jar $JEXAMXML_JAR_FILE "$PARSE_OUT_DIR/$TEST_NAME.out" "$PARSE_REF_OUT_DIR/$TEST_NAME.out" $JEXAMXML_TMP_FILE $JEXAMXML_OPTIONS_FILE > /dev/null);
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

done

########################################################################## INTERPRET

echo "############################### INTERPRET"

for TEST_NAME in stack_test write_test; do

    # Zkontrolujeme návratovou hodnotu.
    if diff "$INT_OUT_DIR/$TEST_NAME.rc" "$INT_REF_OUT_DIR/$TEST_NAME.rc" > /dev/null; then

        # Pokud návratová hodnota je "0", zkontrolujeme i výstup.
        if [[ $(head -n 1 "$INT_REF_OUT_DIR/$TEST_NAME.rc") == "0" ]]; then

            # Porovnání výstupu s referenčním provedeme pomocí diff.
            if diff "$INT_OUT_DIR/$TEST_NAME.out" "$INT_REF_OUT_DIR/$TEST_NAME.out" > /dev/null; then
                echo "*******TEST $TEST_NAME PASSED";
            else
                echo diff "$INT_OUT_DIR/$TEST_NAME.out" "$INT_REF_OUT_DIR/$TEST_NAME.out"
                echo "TEST $TEST_NAME FAILED";
            fi
        # Pokud návratová hodnota není "0", program byl ukončen předčasně a výstup nebyl generován. Test proběhl úspěšně.
        else
            echo "*******TEST $TEST_NAME PASSED";
        fi
    else
        echo "TEST $TEST_NAME FAILED";
    fi

done
