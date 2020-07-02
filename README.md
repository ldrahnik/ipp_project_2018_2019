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
