ASSESSMENT 
==========

10/24b

4/7b - 1. úloha v PHP 7.3 ([assessment report](https://github.com/ldrahnik/ipp_project_2018_2019/issues/7)) \
6/17b - 2. úloha v Pythonu 3.6 a testovací skript v PHP 7.3 ([assessment report](https://github.com/ldrahnik/ipp_project_2018_2019/issues/5))

Analyzátor, interpret a testovací rámec kódu IPPcode19
==========

## Příklad spuštění:

```
php7.3 parse.php --help
Analyzátor kódu v IPPcode19:
      --help vypíše na standardní výstup nápovědu skriptu (nenačítá žádný vstup)
      --stats=file slouží pro zadání souboru file, kam se agregované statistiky
      budou vypisovat (po řádcích dle pořadí v dalších parametrech)
      --loc vypíše do statistik počet řádků s instrukcemi (nepočítají se prázdné
       řádky, ani řádky obsahující pouze komentář, ani úvodní řádek)
      --comments vypíše do statistik počet řádků, na kterých se vyskytoval
      komentář
      --labels vypíše do statistik počet definovaných návěští
      --jumps vypíše do statistik počet instrukcí pro podmíněné a nepodmíněné skoky dohromady
      python3.6 interpret.py --help
```

```
usage: python3.6 interpret.py [--help] [--source SOURCE] [--input INPUT]
                              [--stats STATS] [--insts] [--vars]

Interpret XML reprezentace kódu IPPcode19. Pro správnou funkčnost je nutná
verze Python3.6.

optional arguments:
  --help           Nápověda.
  --source SOURCE  Vstupní soubor s XML reprezentací zdrojového kódu dle
                   definice ze sekce.
  --input INPUT    Soubor se vstupy pro samotnou interpretaci zadaného
                   zdrojového kódu.
  --stats STATS    Sbírání statistik interpretace kódu. Podpora parametru
                   --insts pro výpis počtu vykonaných instrukcí během
                   interpretace do statistik.Podpora parametru --vars pro
                   výpis maximálního počtu inicializovaných proměnných
                   přítomných ve všech platných rámcích během interpretace
                   zadaného programu do statistik.
  --insts
  --vars
```

```
php7.3 test.php --help
Testovací rámec:
      --help vypíše na standardní výstup nápovědu skriptu (nenačítá žádný vstup)
      --directory=path testy bude hledat v zadaném adresáři (chybí-li tento parametr, tak skript prochází aktuální adresář)
      --recursive testy bude hledat nejen v zadaném adresáři, ale i rekurzivně ve všech jeho
        podadresářích
      --parse-script=file soubor se skriptem v PHP 7.3 pro analýzu zdrojového kódu v IPPcode19
        (chybí-li tento parametr, tak implicitní hodnotou je parse.php uložený v aktuálním adresáři)
      --int-script=file soubor se skriptem v Python 3.6 pro interpret XML reprezentace kódu
        v IPPcode19 (chybí-li tento parametr, tak implicitní hodnotou je interpret.py uložený v aktuálním adresáři)
      --testlist=file Slouží pro explicitní zadání seznamu adresářů (zadaných relativními či absolutními cestami) a případně i souborů s testy (zadává se soubor s příponou .src) formou externího souboru file místo načtení testů z aktuálního adresáře (nelze kombinovat s parametrem --directory)
      --match=regexp Slouží pro výběr testů jejichž jmémo je bez přípony (ne cesta) odpovídá zadanému regulárnímu výrazu regexp dle PCRE syntaxe
      --parse-only Bude testován pouze skript pro analýzu zdrojového kódu v IPPcode19 (tento
parametr se nesmí kombinovat s parametrem --int-script)
      --int-only Bude testován pouze skript pro interpret XML reprezentace kódu v IPPcode19
(tento parametr se nesmí kombinovat s parametrem --parse-script)
```

## Testování programu:

```
make test
# pustí projekt s dodanými testy a výstupy uloží do složky
cd ./tests/ && bash _stud_tests.sh  /home/ldrahnik/projects/ipp_project_2018_2019 /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/parse-only/ /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/parse-only/log/ /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/int-only/ /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/int-only/log/ /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/both/ /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/both/log/
# provede porovnání výstupu testů
cd ./tests/ && bash _stud_tests_diff.sh  /home/ldrahnik/projects/ipp_project_2018_2019/jexamxml.jar /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/jexamxml_tmp /home/ldrahnik/projects/ipp_project_2018_2019/tests/options /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/parse-only/ /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/parse-only/log/ /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/int-only/ /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/int-only/log/ /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/both/ /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/both/log/
############################### PARSE
*******TEST read_test PASSED
*******TEST simple_tag PASSED
*******TEST write_test PASSED
############################### INTERPRET
*******TEST stack_test PASSED
*******TEST write_test PASSED
############################### BOTH
############### PARSER
*******TEST error_string_out_of_range PASSED
############### INTERPRET
*******TEST error_string_out_of_range PASSED
############### PARSER
*******TEST read_test PASSED
############### INTERPRET
*******TEST read_test PASSED
############### PARSER
*******TEST simple_program PASSED
############### INTERPRET
*******TEST simple_program PASSED
############### PARSER
*******TEST float PASSED
############### INTERPRET
*******TEST float PASSED
############### PARSER
*******TEST call_stack PASSED
############### INTERPRET
*******TEST call_stack PASSED
# úklid
rm -rf /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/jexamxml_tmp
rm -rf /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/parse-only/log/*
rm -rf /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/int-only/log/*
rm -rf /home/ldrahnik/projects/ipp_project_2018_2019/tests/supplementary-tests/both/log/*
```

## Odevzdané soubory:

```
xdrahn00
├── interpret.py
├── Makefile
├── parse.php
├── readme1.pdf
├── rozsireni
└── test.php

0 directories, 6 files
```
