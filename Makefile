# Name:	Lukáš Drahník
# Project: Zadání projektu z předmětu IPP 2018/2019
# Date: 13.3.2019
# Email: <xdrahn00@stud.fit.vutbr.cz>

PWD	= $(shell pwd)

LOGIN = xdrahn00
FILES = Makefile parse.php rozsireni interpret.py test.php -C doc readme1.pdf

all: tex tar

tar:
	tar -cvzf $(LOGIN).tgz $(FILES)

untar:
	rm -rf $(LOGIN) && mkdir -p $(LOGIN) && tar -C $(LOGIN) -xvzf $(LOGIN).tgz

rmtar:
	rm -f $(LOGIN).tgz

tree:
	tree -a $(LOGIN)

############################################

tex:
	cd doc && make && make readme1.ps && make readme1.pdf

############################################ TESTS

JEXAMXML									= $(PWD)/jexamxml.jar
JEXAMXML_OPTIONS_FILE						= $(PWD)/tests/options
JEXAMXML_TMP_FILE							= $(PWD)/tests/supplementary-tests/jexamxml_tmp


PARSER_TASK_TESTS_DIR						= $(PWD)/tests/supplementary-tests/parse-only/
PARSER_TASK_TESTS_DIR_LOG					= $(PARSER_TASK_TESTS_DIR)log/

INTERPRET_TASK_TESTS_DIR					= $(PWD)/tests/supplementary-tests/int-only/
INTERPRET_TASK_TESTS_DIR_LOG				= $(INTERPRET_TASK_TESTS_DIR)log/

BOTH_TASK_TESTS_DIR							= $(PWD)/tests/supplementary-tests/both/
BOTH_TASK_TESTS_DIR_LOG						= $(BOTH_TASK_TESTS_DIR)log/

SUPPLEMENTARY_TESTS_SCRIPT              	= _stud_tests.sh # <where is located parser & interpret> <parser output dir> <intepret output dir>
SUPPLEMENTARY_TESTS_DIFF_SCRIPT				= _stud_tests_diff.sh # <jexamxml jar file> <jexamxml options file> <output dir> <ref-output dir>

test:
	# pustí projekt s dodanými testy a výstupy uloží do složky
	cd ./tests/ && bash $(SUPPLEMENTARY_TESTS_SCRIPT) $(PWD) $(PARSER_TASK_TESTS_DIR) $(PARSER_TASK_TESTS_DIR_LOG) $(INTERPRET_TASK_TESTS_DIR) $(INTERPRET_TASK_TESTS_DIR_LOG) $(BOTH_TASK_TESTS_DIR) $(BOTH_TASK_TESTS_DIR_LOG)
	
	# provede porovnání výstupu testů
	cd ./tests/ && bash $(SUPPLEMENTARY_TESTS_DIFF_SCRIPT) $(JEXAMXML) $(JEXAMXML_TMP_FILE) $(JEXAMXML_OPTIONS_FILE) $(PARSER_TASK_TESTS_DIR) $(PARSER_TASK_TESTS_DIR_LOG) $(INTERPRET_TASK_TESTS_DIR) $(INTERPRET_TASK_TESTS_DIR_LOG) $(BOTH_TASK_TESTS_DIR) $(BOTH_TASK_TESTS_DIR_LOG)
	
	# úklid
	rm -rf $(JEXAMXML_TMP_FILE)
	rm -rf $(PARSER_TASK_TESTS_DIR_LOG)*
	rm -rf $(INTERPRET_TASK_TESTS_DIR_LOG)*
	rm -rf $(BOTH_TASK_TESTS_DIR_LOG)*
	
