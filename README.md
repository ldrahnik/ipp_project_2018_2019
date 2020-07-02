ASSESSMENT 
==========

10/24b

4/7b - 1. úloha v PHP 7.3 ([assessment report](https://github.com/ldrahnik/ipp_project_2018_2019/issues/7)) \
6/17b - 2. úloha v Pythonu 3.6 a testovací skript v PHP 7.3 ([assessment report](https://github.com/ldrahnik/ipp_project_2018_2019/issues/5))

## Příklad spuštění:

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
