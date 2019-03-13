#!/bin/env python3.6

import argparse, sys
import os
import xml.etree.ElementTree as ET
import re

#
# Interpret XML reprezentace kódu
#
class interpret:


    language = 'IPPcode19';

    GF = {}
    LF = None
    TF = None

    jumpTo = None

    labels = {}

    stats = {}

    instructionOrder = 1

    #
    # Konstruktor volá funkci na parsování argumentů
    # Konstruktor volá funkci run na samotnou intepretaci
    #
    def __init__(self):

        # parsování argumentů z příkazové řádky
        opts = self.parseCmdArgs()

        # interpretace
        self.run(opts)

        return

    #
    # Funkce se volá hned po zavolání konstruktoru.
    # Funkce se stará i intepretaci kódu předaného pomocí souboru argumentem --source
    #
    def run(self, opts):

        try:
            tree = ET.parse(opts.source)
        except ET.ParseError:
            self.error("Nevalidní formát vstupního XML", 52)
        root = tree.getroot()

        # zkontrolování názvu root elementu
        if(root.tag != 'program'):
            self.error('Instrukce musí být ohraničeny tagem program', 31)

        if(root.get('language') != self.language):
            self.error('Instrukce program musí obsahovat atribut language s hodnout: ' + self.language, 31)

        # interpret navíc oproti sekci 3.1 podporuje existenci volitelných dokumentačních textových atributů name a description v kořenovém elementu program
        for arg in root.keys():
            if(arg != 'language' and arg != 'name' and arg != 'description'):
                self.error('Zakázané použití atributu: ' + arg + '. Instrukce program může obsahovat kromě povinného atributu language s hodnotou: ' +
                self.language + ' i atributy name a description bez omezení hodnot', 31)

        # procházení všech instrukcí
        index = 0
        while index <= len(tree.getroot()):

            # nějaká instrukce chtěla skočit
            if(self.jumpTo != None):
                index = self.jumpTo
                self.instructionOrder = self.jumpTo + 1
                self.jumpTo = None
            elif(index == len(tree.getroot())):
                break

            # čti instrukci
            child = tree.getroot()[index]

            if(int(child.get('order')) != self.instructionOrder):
                self.error('Číslování instrukcí není inkrementální po 1, index: ' + str(self.instructionOrder) + ' by měl být: ' + child.get('order'), 31)
            if(child.tag != 'instruction'):
                self.error('Tag pro každou instrukci v tagu program musí být pojmenovaný instruction', 31)
            if(child.get('opcode') == None):
                self.error('Tag pro každou instrukci v tagu program musí obsahovat opcode u kterého nezáleží na velikosti písmen', 31)

            # procházení všech argumentů (kvůli číslování)
            argumentOrder = 1
            for childd in list(child):
                match = re.match(r"arg([0-9]+)", childd.tag, re.I)
                if match:
                    items = match.groups()
                    if(int(items[0]) != argumentOrder):
                        self.error('Tag pro každý operand instrukce musí obsahovat arg + číslo pořadí argumentu inkrementující se o 1, začínající na 1. Argument číslo: ' + str(argumentOrder) + ' má číslo: ' + items[0], 31)
                else:
                    self.error('Tag pro každý operand instrukce musí obsahovat arg + číslo pořadí argumentu inkrementující se o 1, začínající na 1', 31)
                argumentOrder+=1

            # vykonání konkrétní instrukce (zatím nevíme, jestli taková vůbec existuje, zkontrolovali jsme pouze formální stránku XML)
            self.executeInstruction(child.get('opcode'), list(child))
            self.instructionOrder+=1
            index += 1

        # interpret proběhl bez chyby, uložíme statistiky do souboru dle pořadí
        if(opts.stats != None):
            try:
                f = open(opts.stats, "w")
            except:
                self.error('Nepodařilo se otevřít soubor pro zápis statistik: ' + opts.stats,12)
            f.truncate()
            for info in self.stats:
                f.write(str(self.stats[info]) + "\n")
            f.close()

        sys.exit(0)

    #
    # Funkce slouží pro rozdělení symbolu podle zavináče a vrací Value. Type@Value
    #
    def getSymbValue(self, arg):
        return arg.text.split("@")[1]

    #
    # Funkce slouží pro rozdělení symbolu podle zavináče a vrací Type. Type@Value
    #
    def getSymbType(self, arg):
        return arg.text.split("@")[0]

    #
    # Funkce slouží pro validování názvu pro návěští.
    #
    def isValidLabelName(self, arg):
        if(arg.get("type") != 'label'):
            return False
        if(re.match('[a-zA-Z0-9_\-$&%*]+$', arg.text) == None):
            return False
        return True

    #
    # Funkce slouží pro validování návěští, zda již náhodou neexistuje stejného názvu.
    #
    def isValidLabel(self, arg):
        if(self.labels.get(arg.text, None) == None):
            return False
        return True

    #
    # Funkce slouží pro kontrolu názvu proměnné předané v arg
    #
    # Identifikátor proměnné se skládá ze dvou částí oddělených
    # zavináčem (znak @; bez bílých znaků), označení rámce LF, TF nebo GF a samotného jména proměnné
    # (sekvence libovolných alfanumerický a speciálních znaků bez bílých znaků začínající písmenem nebo
    # speciálním znakem, kde speciální znaky jsou: , -, $, &, %, *). Např. GF@ x značí proměnnou x
    # uloženou v globálním rámci.
    #
    def isValidVar(self, arg):
        if(arg.get("type") != 'var'):
            return False
        if(re.match('^(LF|TF|GF){1}@[a-zA-Z_\-$&%*]{1}[a-zA-Z0-9_\-$&%*]*$', arg.text) == None):
            return False
        return True

    #
    # Funkce slouží pro kontrolu názvu konstanty předané parametrem arg
    #
    def isValidConstant(self, arg):
        bool = False
        if(arg.get("type") == "bool" and re.match('^(true|false)$', arg.text) != None):
            bool = True
        int = False
        if(arg.get("type") == "int" and re.match('^[-]?[0-9]*$', arg.text) != None):
            int = True
        string = False
        # speciální výjimka pro prázdný strig
        if(arg.get("type") == "string" and (not arg.text or re.match('^.*$', arg.text) != None)):
            string = True

        if(string == True or int == True or bool == True):
            return True;

        return False

    #
    # Funkce kontroluje, zda je zadaný type symbolu správný, jestliže platí Type ∈ {int, string, bool} vrací true, pakliže ne, false.
    #
    def isValidType(self, arg):
        if(arg.get("type") != 'type'):
            return False
        if(re.match('^(string|int|bool){1}$', arg.text) == None):
            return False
        return True

    #
    # Funkce slouží pro kontrolu názvu symbolu předané parametrem arg, symbol se může skládat buď z proměnné nebo konstanty
    #
    def isValidSymb(self, arg):
        return self.isValidVar(arg) or self.isValidConstant(arg)

    #
    # Instruction DEFVAR
    #
    def defVarIns(self, args):
        if(len(args) != 1):
            self.error('U instrukce DEFVAR musí být počet argumentů roven 1', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable není povolená nebo musí mít type var, type uvedený', 53)
        if(self.getSymbType(args[0]) == 'GF'):
            self.GF[self.getSymbValue(args[0])] = {"value": None, "type": None};

        # if(self.getSymbType(args[0]) == 'LF'): TODO:
        #    self.LF[self.getSymbValue(args[0])];
        # if(self.getSymbType(args[0]) == 'TF'):
        #    self.TF[self.getSymbValue(args[0])];

    #
    # Instruction WRITE
    #
    def writeIns(self, args):
        if(len(args) != 1):
            self.error('U instrukce WRITE musí být počet argumentů roven 1', 52)
        if(self.isValidSymb(args[0]) == False):
            self.error('Symbol není validní', 53)

        if(self.isValidVar(args[0]) == False):
            if(self.getSymbType(args[0]) == 'bool'):
                print(args[0].text) # TODO: bool
            else:
                print(args[0].text)
        else:
            if(self.getSymbType(args[0]) == 'GF'):
                if(self.getSymbValue(args[0]) not in self.GF):
                    self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
                if(self.GF.get(self.getSymbValue(args[0])).get("type") == "bool"):
                    print(self.GF.get(self.getSymbValue(args[0])).get("value")) # TODO: bool
                else:
                    print(self.GF.get(self.getSymbValue(args[0])).get("value"))
            else:
                print(self.getSymbType(args[0]))
            # TODO: LF, TF

    #
    # Instruction BREAK
    #
    def breakIns(self, args):
        print('Global Frame: ' + str(self.GF), file=sys.stderr)
        print('Local Frame: ' + str(self.LF), file=sys.stderr)
        print('Temporary Frame: ' + str(self.TF), file=sys.stderr)
        if((self.stats.get('--insts', None) != None)):
            print('Provedené instrukce: ' + str(self.stats['--insts']), file=sys.stderr)
        if((self.stats.get('--vars', None) != None)):
            print('Maximální počet inicializovaných proměnných ve všech rámcích: ' + str(self.stats['--vars']), file=sys.stderr)

    #
    # Instruction MOVE
    #
    def moveIns(self, args):
        if(len(args) != 2):
            self.error('U instrukce MOVE musí být počet argumentů roven 2', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.getSymbType(args[0]) == 'GF'):
            if(self.getSymbValue(args[0]) not in self.GF):
                self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
            value = ""
            if(args[1].text):
                value = args[1].text
            self.GF[self.getSymbValue(args[0])] = {"value": value, "type": args[1].get("type")}
        # TODO: LF, TF

    #
    # Instruction ADD
    #
    def addIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce ADD musí být počet argumentů roven 2', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)
        if(self.getSymbValue(args[0]) not in self.GF or
          (self.GF.get(self.getSymbValue(args[0])).get('type') != 'int' and
          self.GF.get(self.getSymbValue(args[0])).get('type') != None)): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)

        # value1
        value1 = 0
        if(self.isValidVar(args[1]) == True):
            if(self.GF.get(self.getSymbValue(args[1])).get('type') != 'int'):
                 self.error('Symbol není validní', 53)
            value1 = self.GF.get(self.getSymbValue(args[1])).get('value')
        else:
            if(args[1].get("type") != 'int'):
                self.error('Symbol není validní', 53)
            value1 = args[1].text

        # value2
        value2 = 0
        if(self.isValidVar(args[2]) == True):
            if(self.GF.get(self.getSymbValue(args[2])).get('type') != 'int'):
                 self.error('Symbol není validní', 53)
            value2 = self.GF.get(self.getSymbValue(args[2])).get('value')
        else:
            if(args[2].get("type") != 'int'):
                self.error('Symbol není validní', 53)
            value2 = args[2].text

        # spočítání a uložení výsledku
        result = int(value1) + int(value2)
        self.GF[self.getSymbValue(args[0])] = {"value": result, "type": "int"}

    #
    # Instruction MUL
    #
    def mulIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce MUL musí být počet argumentů roven 2', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)
        if(self.getSymbValue(args[0]) not in self.GF or
          (self.GF.get(self.getSymbValue(args[0])).get('type') != 'int' and
          self.GF.get(self.getSymbValue(args[0])).get('type') != None)): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)

        # value1
        value1 = 0
        if(self.isValidVar(args[1]) == True):
            if(self.GF.get(self.getSymbValue(args[1])).get('type') != 'int'):
                 self.error('Symbol není validní', 53)
            value1 = self.GF.get(self.getSymbValue(args[1])).get('value')
        else:
            if(args[1].get("type") != 'int'):
                self.error('Symbol není validní', 53)
            value1 = args[1].text

        # value2
        value2 = 0
        if(self.isValidVar(args[2]) == True):
            if(self.GF.get(self.getSymbValue(args[2])).get('type') != 'int'):
                 self.error('Symbol není validní', 53)
            value2 = self.GF.get(self.getSymbValue(args[2])).get('value')
        else:
            if(args[2].get("type") != 'int'):
                self.error('Symbol není validní', 53)
            value2 = args[2].text

        # spočítání a uložení výsledku
        result = int(value1) * int(value2)
        self.GF[self.getSymbValue(args[0])] = {"value": result, "type": "int"}

    #
    # Instruction IDIV
    #
    def idivIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce IDIV musí být počet argumentů roven 2', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)
        if(self.getSymbValue(args[0]) not in self.GF or
          (self.GF.get(self.getSymbValue(args[0])).get('type') != 'int' and
          self.GF.get(self.getSymbValue(args[0])).get('type') != None)): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)

        # value1
        value1 = 0
        if(self.isValidVar(args[1]) == True):
            if(self.GF.get(self.getSymbValue(args[1])).get('type') != 'int'):
                 self.error('Symbol není validní', 53)
            value1 = self.GF.get(self.getSymbValue(args[1])).get('value')
        else:
            if(args[1].get("type") != 'int'):
                self.error('Symbol není validní', 53)
            value1 = args[1].text

        if(int(value1) == 0):
            self.error('Nelze dělit nulou', 58)

        # value2
        value2 = 0
        if(self.isValidVar(args[2]) == True):
            if(self.GF.get(self.getSymbValue(args[2])).get('type') != 'int'):
                 self.error('Symbol není validní', 53)
            value2 = self.GF.get(self.getSymbValue(args[2])).get('value')
        else:
            if(args[2].get("type") != 'int'):
                self.error('Symbol není validní', 53)
            value2 = args[2].text

        # spočítání a uložení výsledku
        result = int(int(value2) / int(value1))
        self.GF[self.getSymbValue(args[0])] = {"value": result, "type": "int"}

    #
    # Instruction SUB
    #
    def subIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce SUB musí být počet argumentů roven 2', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)
        if(self.getSymbValue(args[0]) not in self.GF or
          (self.GF.get(self.getSymbValue(args[0])).get('type') != 'int' and
          self.GF.get(self.getSymbValue(args[0])).get('type') != None)): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)

        # value1
        value1 = 0
        if(self.isValidVar(args[1]) == True):
            if(self.GF.get(self.getSymbValue(args[1])).get('type') != 'int'):
                 self.error('Symbol není validní', 53)
            value1 = self.GF.get(self.getSymbValue(args[1])).get('value')
        else:
            if(args[1].get("type") != 'int'):
                self.error('Symbol není validní', 53)
            value1 = args[1].text

        # value2
        value2 = 0
        if(self.isValidVar(args[2]) == True):
            if(self.GF.get(self.getSymbValue(args[2])).get('type') != 'int'):
                 self.error('Symbol není validní', 53)
            value2 = self.GF.get(self.getSymbValue(args[2])).get('value')
        else:
            if(args[2].get("type") != 'int'):
                self.error('Symbol není validní', 53)
            value2 = args[2].text

        # spočítání a uložení výsledku
        result = int(value1) - int(value2)
        self.GF[self.getSymbValue(args[0])] = {"value": result, "type": "int"}

    #
    # Instruction DPRINT
    #
    def dprintIns(self, args):
        if(len(args) != 1):
            self.error('U instrukce DPRINT musí být počet argumentů roven 1', 52)
        if(self.isValidSymb(args[0]) == False):
            self.error('Symbol není validní', 53)

        if(self.isValidVar(args[0]) == False):
            if(self.getSymbType(args[0]) == 'bool'):
                print(args[0].text, file=sys.stderr) # TODO: bool
            else:
                print(args[0].text, file=sys.stderr)
        else:
            if(self.getSymbType(args[0]) == 'GF'):
                if(self.getSymbValue(args[0]) not in self.GF):
                    self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
                if(self.GF.get(self.getSymbValue(args[0])).get("type") == "bool"):
                    print(self.GF.get(self.getSymbValue(args[0])).get("value"), file=sys.stderr) # TODO: bool
                else:
                    print(self.GF.get(self.getSymbValue(args[0])).get("value"), file=sys.stderr)
            else:
                print(self.getSymbType(args[0]), file=sys.stderr)
            # TODO: LF, TF

    #
    # Instruction AND
    #
    def andIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce AND musí být počet argumentů roven 3', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
        elif(self.GF.get(self.getSymbValue(args[0])).get("type") != "bool" and
            self.GF.get(self.getSymbValue(args[0])).get("type") != None):
            self.error('Proměnná není bool', 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)

        # value1
        value1 = None
        if(self.isValidVar(args[1]) == True):
            if(self.GF.get(self.getSymbValue(args[1])).get('type') != 'bool'):
                self.error('Symbol není validní', 53)
            value1 = self.GF.get(self.getSymbValue(args[1])).get('value')
        else:
            if(args[1].get("type") != 'bool'):
                self.error('Symbol není validní', 53)
            value1 = args[1].text

        # value2
        value2 = None
        if(self.isValidVar(args[2]) == True):
            if(self.GF.get(self.getSymbValue(args[2])).get('type') != 'bool'):
                self.error('Symbol není validní', 53)
            value2 = self.GF.get(self.getSymbValue(args[2])).get('value')
        else:
            if(args[2].get("type") != 'bool'):
                self.error('Symbol není validní', 53)
            value2 = args[2].text

        # logický součin - AND
        result = None
        if(value1 == "true" and value2 == "true"):
            result = "true"
        else:
            result = "false"
        self.GF[self.getSymbValue(args[0])] = {"value": result, "type": "bool"}

    #
    # Instruction OR
    #
    def orIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce OR musí být počet argumentů roven 3', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
        elif(self.GF.get(self.getSymbValue(args[0])).get("type") != "bool" and
            self.GF.get(self.getSymbValue(args[0])).get("type") != None):
            self.error('Proměnná není bool', 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)

        # value1
        value1 = None
        if(self.isValidVar(args[1]) == True):
            if(self.GF.get(self.getSymbValue(args[1])).get('type') != 'bool'):
                self.error('Symbol není validní', 53)
            value1 = self.GF.get(self.getSymbValue(args[1])).get('value')
        else:
            if(args[1].get("type") != 'bool'):
                self.error('Symbol není validní', 53)
            value1 = args[1].text

        # value2
        value2 = None
        if(self.isValidVar(args[2]) == True):
            if(self.GF.get(self.getSymbValue(args[2])).get('type') != 'bool'):
                self.error('Symbol není validní', 53)
            value2 = self.GF.get(self.getSymbValue(args[2])).get('value')
        else:
            if(args[2].get("type") != 'bool'):
                self.error('Symbol není validní', 53)
            value2 = args[2].text

        # logický součet - OR
        result = None
        if(value1 == "true" or value2 == "true"):
            result = "true"
        else:
            result = "false"
        self.GF[self.getSymbValue(args[0])] = {"value": result, "type": "bool"}

    #
    # Instruction LABEL
    #
    def labelIns(self, args):
        if(len(args) != 1):
            self.error('U instrukce LABEL musí být počet argumentů roven 1', 52)
        if(self.isValidLabelName(args[0]) == False):
            self.error('Není validní label', 52)
        if(self.isValidLabel(args[0]) == True):
            self.error('Redefinice návěští není možná', 52)

        self.labels[args[0].text] = self.instructionOrder

    #
    # Instruction JUMP
    #
    def jumpIns(self, args):
        if(len(args) != 1):
            self.error('U instrukce JUMP musí být počet argumentů roven 1', 52)
        if(self.isValidLabelName(args[0]) == False):
            self.error('Není validní label', 52)
        if(self.isValidLabel(args[0]) == False):
            self.error('Návěští musí existovat', 52)
        self.jumpTo = self.labels[args[0].text]

    #
    # Instruction JUMPIFEQ
    #
    def jumpifeqIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce JUMPIFEQ musí být počet argumentů roven 3', 52)
        if(self.isValidLabelName(args[0]) == False):
            self.error('Není validní label', 52)
        if(self.isValidLabel(args[0]) == False):
            self.error('Návěští musí existovat', 52)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)

        # zjisti type1, value1
        type1 = None
        value1 = None
        if(self.isValidVar(args[1]) == True):
            type1 = self.GF.get(self.getSymbValue(args[1])).get('type')
            value1 = self.GF.get(self.getSymbValue(args[1])).get('value')
        else:
            type1 = args[2].get("type")
            value1 = args[2].text

        # zjistit type2, value2
        type2 = None
        value2 = None
        if(self.isValidVar(args[2]) == True):
            type2 = self.GF.get(self.getSymbValue(args[2])).get('type')
            value2 = self.GF.get(self.getSymbValue(args[2])).get('value')
        else:
            type2 = args[2].get("type")
            value2 = args[2].text

        # porovnej type1, type2 (53)
        if(type1 != type2):
            self.error('Typy se musejí rovnat', 53)

        # porovnej value1, value2
        if(str(value1) == str(value2)):
            self.jumpTo = self.labels[args[0].text]

    #
    # Instruction JUMPIFNEQ
    #
    def jumpifneqIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce JUMPIFNEQ musí být počet argumentů roven 3', 52)
        if(self.isValidLabelName(args[0]) == False):
            self.error('Není validní label', 52)
        if(self.isValidLabel(args[0]) == False):
            self.error('Návěští musí existovat', 52)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)

        # zjisti type1, value1
        type1 = None
        value1 = None
        if(self.isValidVar(args[1]) == True):
            type1 = self.GF.get(self.getSymbValue(args[1])).get('type')
            value1 = self.GF.get(self.getSymbValue(args[1])).get('value')
        else:
            type1 = args[2].get("type")
            value1 = args[2].text

        # zjistit type2, value2
        type2 = None
        value2 = None
        if(self.isValidVar(args[2]) == True):
            type2 = self.GF.get(self.getSymbValue(args[2])).get('type')
            value2 = self.GF.get(self.getSymbValue(args[2])).get('value')
        else:
            type2 = args[2].get("type")
            value2 = args[2].text

        # porovnej type1, type2 (53)
        if(type1 != type2):
            self.error('Typy se musejí rovnat', 53)

        # porovnej value1, value2
        if(str(value1) != str(value2)):
            self.jumpTo = self.labels[args[0].text]

    #
    # Instruction STRI2INT
    #
    def stri2intIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce STRI2INT musí být počet argumentů roven 3', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
        elif(self.GF.get(self.getSymbValue(args[0])).get("type") != "int" and
            self.GF.get(self.getSymbValue(args[0])).get("type") != None):
            self.error('Proměnná není int', 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)

        # získání pozice
        position = 0
        if(self.isValidVar(args[2]) == False):
            if(args[2].get("type") != 'int'):
                self.error('Symbol není int', 53)
            position = int(args[2].text)
        else:
            if(self.GF.get(self.getSymbValue(args[2])).get("type") != "int"):
                self.error('Symbol není int', 53)
            position = int(self.GF.get(self.getSymbValue(args[2])).get("value"))

        # získání znaku
        char = 0
        if(self.isValidVar(args[1]) == False):
            if(args[1].get("type") != 'string'):
                self.error('Symbol není string', 53)

            # indexace mimo daný řetězec vede na chybu 58
            if(position >= len(args[1].text)):
                self.error('Indexace mimo daný řetězec', 58)

            char = ord(args[1].text[position])
        else:
            if(self.GF.get(self.getSymbValue(args[1])).get("type") != "string"):
                self.error('Symbol není string', 53)

            # indexace mimo daný řetězec vede na chybu 58
            if(position >= len(self.GF.get(self.getSymbValue(args[1])).get("value"))):
                self.error('Indexace mimo daný řetězec', 58)

            char = ord(self.GF.get(self.getSymbValue(args[1])).get("value")[position])

        # uložení ordinální hodnoty znaku z pozice
        self.GF[self.getSymbValue(args[0])] = {"value": char, "type": "string"}

    #
    # Instruction NOT
    #
    def notIns(self, args):
        if(len(args) != 2):
            self.error('U instrukce NOT musí být počet argumentů roven 2', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
        elif(self.GF.get(self.getSymbValue(args[0])).get("type") != "bool" and
            self.GF.get(self.getSymbValue(args[0])).get("type") != None):
            self.error('Proměnná není bool', 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)

        # value
        value1 = None
        if(self.isValidVar(args[1]) == True):
            if(self.GF.get(self.getSymbValue(args[1])).get('type') != 'bool'):
                self.error('Symbol není validní', 53)
            value1 = self.GF.get(self.getSymbValue(args[1])).get('value')
        else:
            if(args[1].get("type") != 'bool'):
                self.error('Symbol není validní', 53)
            value1 = args[1].text

        # logická negace - NOT
        result = None
        if(value1 == "false"):
            result = "true"
        else:
            result = "false"
        self.GF[self.getSymbValue(args[0])] = {"value": result, "type": "bool"}

    #
    # Instruction STRLEN
    #
    def strlenIns(self, args):
        if(len(args) != 2):
            self.error('U instrukce STRLEN musí být počet argumentů roven 2', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)

        # zjištění délky
        var_len = 0
        if(self.isValidVar(args[1]) == False):
            if(args[1].get("type") != 'string'):
                self.error('Symbol není string', 53)
            var_len = len(args[1].text)
        else:
            if(self.GF.get(self.getSymbValue(args[1])).get("type") != "string"):
                self.error('Symbol není string', 53)
            var_len = len(self.GF.get(self.getSymbValue(args[1])).get("value"))

        # uložení délky na správné místo
        if(self.getSymbType(args[0]) == 'GF'): # TODO: LF, TF
            if(self.getSymbValue(args[0]) not in self.GF):
                self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
            if(self.GF.get(self.getSymbValue(args[0])).get("type") != "int" and
               self.GF.get(self.getSymbValue(args[0])).get("type") != None):
               self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
            self.GF[self.getSymbValue(args[0])] = {"value": var_len, "type": "int"}

    #
    # Instruction GETCHAR
    #
    def getcharIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce GETCHAR musí být počet argumentů roven 3', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
        elif(self.GF.get(self.getSymbValue(args[0])).get("type") != "string" and
            self.GF.get(self.getSymbValue(args[0])).get("type") != None):
            self.error('Proměnná není string', 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)

        # získání pozice
        position = 0
        if(self.isValidVar(args[2]) == False):
            if(args[2].get("type") != 'int'):
                self.error('Symbol není int', 53)
            position = int(args[2].text)
        else:
            if(self.GF.get(self.getSymbValue(args[2])).get("type") != "int"):
                self.error('Symbol není int', 53)
            position = int(self.GF.get(self.getSymbValue(args[2])).get("value"))

        # získání znaku
        char = ""
        if(self.isValidVar(args[1]) == False):
            if(args[1].get("type") != 'string'):
                self.error('Symbol není string', 53)

            # indexace mimo daný řetězec vede na chybu 58
            if(position >= len(args[1].text)):
                self.error('Indexace mimo daný řetězec', 58)

            char = args[1].text[position]
        else:
            if(self.GF.get(self.getSymbValue(args[1])).get("type") != "string"):
                self.error('Symbol není string', 53)

            # indexace mimo daný řetězec vede na chybu 58
            if(position >= len(self.GF.get(self.getSymbValue(args[1])).get("value"))):
                self.error('Indexace mimo daný řetězec', 58)

            char = self.GF.get(self.getSymbValue(args[1])).get("value")[position]

        # uložení znaku z pozice
        self.GF[self.getSymbValue(args[0])] = {"value": char, "type": "string"}


    #
    # Instruction LT
    #
    def ltIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce LT musí být počet argumentů roven 3', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
        elif(self.GF.get(self.getSymbValue(args[0])).get("type") != "bool" and
            self.GF.get(self.getSymbValue(args[0])).get("type") != None):
            self.error('Proměnná není bool', 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)

        # zjisti type1, value1
        type1 = None
        value1 = None
        if(self.isValidVar(args[1]) == True):
            type1 = self.GF.get(self.getSymbValue(args[1])).get('type')
            value1 = self.GF.get(self.getSymbValue(args[1])).get('value')
        else:
            type1 = args[1].get("type")
            value1 = args[1].text

        # zjistit type2, value2
        type2 = None
        value2 = None
        if(self.isValidVar(args[2]) == True):
            type2 = self.GF.get(self.getSymbValue(args[2])).get('type')
            value2 = self.GF.get(self.getSymbValue(args[2])).get('value')
        else:
            type2 = args[2].get("type")
            value2 = args[2].text

        # porovnej type1, type2 (53)
        if(type1 != type2):
            self.error('Typy se musejí rovnat', 53)

        # porovnej value1, value2
        if(str(value1) < str(value2)):
            result = "true"
        else:
            result = "false"

        self.GF[self.getSymbValue(args[0])] = {"value": result, "type": "bool"}


    #
    # Instruction EQ
    #
    def eqIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce LT musí být počet argumentů roven 3', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable není povolená nebo musí mít type var, type uvedený', 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
        elif(self.GF.get(self.getSymbValue(args[0])).get("type") != "bool" and
            self.GF.get(self.getSymbValue(args[0])).get("type") != None):
            self.error('Proměnná není bool', 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)

        # zjisti type1, value1
        type1 = None
        value1 = None
        if(self.isValidVar(args[1]) == True):
            type1 = self.GF.get(self.getSymbValue(args[1])).get('type')
            value1 = self.GF.get(self.getSymbValue(args[1])).get('value')
        else:
            type1 = args[1].get("type")
            value1 = args[1].text

        # zjistit type2, value2
        type2 = None
        value2 = None
        if(self.isValidVar(args[2]) == True):
            type2 = self.GF.get(self.getSymbValue(args[2])).get('type')
            value2 = self.GF.get(self.getSymbValue(args[2])).get('value')
        else:
            type2 = args[2].get("type")
            value2 = args[2].text

        # porovnej type1, type2 (53)
        if(type1 != type2):
            self.error('Typy se musejí rovnat', 53)

        # porovnej value1, value2
        if(str(value1) == str(value2)):
            result = "true"
        else:
            result = "false"

        self.GF[self.getSymbValue(args[0])] = {"value": result, "type": "bool"}

    #
    # Instruction GT
    #
    def gtIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce LT musí být počet argumentů roven 3', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
        elif(self.GF.get(self.getSymbValue(args[0])).get("type") != "bool" and
            self.GF.get(self.getSymbValue(args[0])).get("type") != None):
            self.error('Proměnná není bool', 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)

        # zjisti type1, value1
        type1 = None
        value1 = None
        if(self.isValidVar(args[1]) == True):
            type1 = self.GF.get(self.getSymbValue(args[1])).get('type')
            value1 = self.GF.get(self.getSymbValue(args[1])).get('value')
        else:
            type1 = args[1].get("type")
            value1 = args[1].text

        # zjistit type2, value2
        type2 = None
        value2 = None
        if(self.isValidVar(args[2]) == True):
            type2 = self.GF.get(self.getSymbValue(args[2])).get('type')
            value2 = self.GF.get(self.getSymbValue(args[2])).get('value')
        else:
            type2 = args[2].get("type")
            value2 = args[2].text

        # porovnej type1, type2 (53)
        if(type1 != type2):
            self.error('Typy se musejí rovnat', 53)

        # porovnej value1, value2
        if(str(value1) > str(value2)):
            result = "true"
        else:
            result = "false"

        self.GF[self.getSymbValue(args[0])] = {"value": result, "type": "bool"}
    #
    # Instruction SETCHAR
    #
    def setcharIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce SETCHAR musí být počet argumentů roven 3', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
        elif(self.GF.get(self.getSymbValue(args[0])).get("type") != "string" and
            self.GF.get(self.getSymbValue(args[0])).get("type") != None):
            self.error('Proměnná není string', 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)

        # získání pozice
        position = 0
        if(self.isValidVar(args[1]) == False):
            if(args[1].get("type") != 'int'):
                self.error('Symbol není int', 53)
            position = int(args[1].text)
        else:
            if(self.GF.get(self.getSymbValue(args[1])).get("type") != "int"):
                self.error('Symbol není int', 53)
            position = int(self.GF.get(self.getSymbValue(args[1])).get("value"))

        # získání znaku
        char = ""
        if(self.isValidVar(args[2]) == False):
            if(args[2].get("type") != 'string'):
                self.error('Symbol není string', 53)
            char = args[2].text[0]
        else:
            if(self.GF.get(self.getSymbValue(args[2])).get("type") != "string"):
                self.error('Symbol není string', 53)
            char = self.GF.get(self.getSymbValue(args[2])).get("value")[0]

        # indexace mimo daný řetězec vede na chybu 58
        if(position >= len(self.GF.get(self.getSymbValue(args[0])).get("value"))):
            self.error('Indexace mimo daný řetězec', 58)

        # uložení znaku do proměnné na pozici
        newString = list(self.GF.get(self.getSymbValue(args[0])).get("value"))
        newString[position] = char
        self.GF[self.getSymbValue(args[0])] = {"value": "".join(newString), "type": "string"} # TODO: LF, TF

    #
    # Instruction TYPE
    #
    def typeIns(self, args):
        if(len(args) != 2):
            self.error('U instrukce TYPE musí být počet argumentů roven 2', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)

        # zjištění typu
        type = ""
        if(self.isValidVar(args[1]) == False):
            type = args[1].get("type")
        else:
            type = self.GF.get(self.getSymbValue(args[1])).get("type")

        # uložení typu
        if(self.getSymbType(args[0]) == 'GF'): # TODO: LF, TF
            if(self.getSymbValue(args[0]) not in self.GF):
                self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
            if(self.GF.get(self.getSymbValue(args[0])).get("type") != "string" and
               self.GF.get(self.getSymbValue(args[0])).get("type") != None):
               self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
            self.GF[self.getSymbValue(args[0])] = {"value": type, "type": "string"}

    #
    # Instruction CONTAC
    #
    def concatIns(self, args):
        if(len(args) != 3):
            self.error('U instrukce CONCAT musí být počet argumentů roven 3', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
        elif(self.GF.get(self.getSymbValue(args[0])).get("type") != "string" and
            self.GF.get(self.getSymbValue(args[0])).get("type") != None):
            self.error('Proměnná není string', 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)
        if(self.isValidSymb(args[2]) == False):
            self.error('Symbol není validní', 53)

        # value1
        value1 = ""
        if(self.isValidVar(args[1]) == True):
            if(self.GF.get(self.getSymbValue(args[1])).get('type') != 'string'):
                self.error('Symbol není validní', 53)
            value1 = self.GF.get(self.getSymbValue(args[1])).get('value')
        else:
            if(args[1].get("type") != 'string'):
                self.error('Symbol není validní', 53)
            value1 = args[1].text

        # value2
        value2 = ""
        if(self.isValidVar(args[2]) == True):
            if(self.GF.get(self.getSymbValue(args[2])).get('type') != 'string'):
                self.error('Symbol není validní', 53)
            value2 = self.GF.get(self.getSymbValue(args[2])).get('value')
        else:
            if(args[2].get("type") != 'string'):
                self.error('Symbol není validní', 53)
            value2 = args[2].text

        # konkatenace
        result = value1 + value2
        self.GF[self.getSymbValue(args[0])] = {"value": result, "type": "string"}

    #
    # Instruction INT2CHAR
    #
    def int2charIns(self, args):
        if(len(args) != 2):
            self.error('U instrukce INT2CHAR musí být počet argumentů roven 2', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)
        elif(self.GF.get(self.getSymbValue(args[0])).get("type") != "string" and
            self.GF.get(self.getSymbValue(args[0])).get("type") != None):
            self.error('Proměnná není int', 53)
        if(self.isValidSymb(args[1]) == False):
            self.error('Symbol není validní', 53)

        # získání pozice
        position = 0
        if(self.isValidVar(args[1]) == False):
            if(args[1].get("type") != 'int'):
                self.error('Symbol není int', 53)
            position = int(args[1].text)
        else:
            if(self.GF.get(self.getSymbValue(args[1])).get("type") != "int"):
                self.error('Symbol není int', 53)
            position = int(self.GF.get(self.getSymbValue(args[1])).get("value"))

        # získání znaku
        char = ""
        if(self.isValidVar(args[1]) == False):
            if(args[1].get("type") != 'int'):
                self.error('Symbol není string', 53)
            try:
                char = chr(int(args[1].text))
            except (ValueError):
                # Není-li symb validní ordinální hodnota znaku v Unicode dojde k chybě 58.
                self.error('Není validní ordinální hodnota znaku v Unicode', 58)
        else:
            if(self.GF.get(self.getSymbValue(args[1])).get("type") != "int"):
                self.error('Symbol není int', 53)

            try:
                char = chr(int(self.GF.get(self.getSymbValue(args[1])).get("value")))
            except (ValueError):
                # Není-li symb validní ordinální hodnota znaku v Unicode dojde k chybě 58.
                self.error('Není validní ordinální hodnota znaku v Unicode', 58)

        # nastavení hodnoty
        self.GF[self.getSymbValue(args[0])] = {"value": char, "type": "string"}

    #
    # Instruction READ
    #
    def readIns(self, args):
        if(len(args) != 2):
            self.error('U instrukce READ musí být počet argumentů roven 2', 52)
        if(self.isValidVar(args[0]) == False):
            self.error('Hodnota ve variable: ' + args[0].text + ' není povolená nebo musí mít type var, type uvedený: ' + arg[0].get("type"), 53)
        if(self.isValidType(args[1]) == False):
            self.error('Type není validní, musí být z množiny int, bool, string', 53)
        if(self.getSymbValue(args[0]) not in self.GF): # TODO: LF, TF
            self.error('Proměnná:' + self.getSymbValue(args[0]) + ' na GF neexistuje', 54)

        type = args[1].text
        value = input()
        if(type == "string"):
            try:
                value = str(value)
            except (ValueError, TypeError):
                value = ""
        if(type == "int"):
            try:
                value = int(value)
            except (ValueError, TypeError):
                value = 0
        if(type == "bool"):
            if(value.upper() == "TRUE"):
                value = "true"
            else:
                value = "false"

        self.GF[self.getSymbValue(args[0])] = {"value": value, "type": type}

    #
    # Funkce obstarává zavolání pro každou instrukci zvlášť, opcode v xml buď odpovídá některé z povolených instrukcí nebo funkce skončí chybou.
    # Parametry: opcode a argumenty(args) pro danou instrukci.
    #
    def executeInstruction(self, opcode, args):
        upperOpCode = opcode.upper()

        if(upperOpCode == 'MOVE'):
            self.moveIns(args)
        elif(upperOpCode == 'INT2CHAR'):
            self.int2charIns(args)
            #'CREATEFRAME':
            #'PUSHFRAME':
            #'RETURN':
        elif(upperOpCode == 'BREAK'):
            self.breakIns(args)

            #'POPS':
        elif(upperOpCode == 'DEFVAR'):
            self.defVarIns(args)
            #'CALL':
            #'PUSHS':
        elif(upperOpCode == 'WRITE'):
            self.writeIns(args)
        elif(upperOpCode == 'DPRINT'):
            self.dprintIns(args)

        elif(upperOpCode == 'ADD'):
            self.addIns(args)
        elif(upperOpCode == 'SUB'):
            self.subIns(args)
        elif(upperOpCode == 'MUL'):
            self.mulIns(args)
        elif(upperOpCode == 'IDIV'):
            self.idivIns(args)
        elif(upperOpCode == 'LT'):
            self.ltIns(args)
        elif(upperOpCode == 'EQ'):
            self.eqIns(args)
        elif(upperOpCode == 'GT'):
            self.gtIns(args)
        elif(upperOpCode == 'AND'):
            self.andIns(args)
        elif(upperOpCode == 'OR'):
            self.orIns(args)
        elif(upperOpCode == 'NOT'):
            self.notIns(args)
        elif(upperOpCode == 'STRI2INT'):
            self.stri2intIns(args)
        elif(upperOpCode == 'CONCAT'):
            self.concatIns(args)
        elif(upperOpCode == 'GETCHAR'):
            self.getcharIns(args)
        elif(upperOpCode == 'SETCHAR'):
            self.setcharIns(args)

        elif(upperOpCode == 'READ'):
            self.readIns(args)

        elif(upperOpCode == 'STRLEN'):
            self.strlenIns(args)
        elif(upperOpCode == 'TYPE'):
            self.typeIns(args)

        elif(upperOpCode == 'LABEL'):
            self.labelIns(args)
        elif(upperOpCode == 'JUMP'):
            self.jumpIns(args)
        elif(upperOpCode == 'JUMPIFEQ'):
            self.jumpifeqIns(args)
        elif(upperOpCode == 'JUMPIFNEQ'):
            self.jumpifneqIns(args)

        # neznámý operační kód
        else:
            self.error('Instrukce: ' + opcode.upper() + ' neexistuje', 32)

        # instrukci se podařilo provést bez erroru, inkrementujeme provedené instrukce
        if(self.stats.get('--insts', None) != None):
            self.stats['--insts'] += 1

        # prochází všechny frames a sečte proměnné, které nejsou icinializované, porovná a případně uloží do statistik
        var_count = 0
        for gvar in self.GF:
            if(self.GF[gvar].get("value") != None):
                var_count += 1
        if(self.LF != None):
            for gvar in self.LF:
                if(self.LF[gvar].get("value") != None):
                    var_count += 1
        if(self.TF != None):
            for gvar in self.TF:
                if(self.TF[gvar].get("value") != None):
                    var_count += 1
        if(self.stats.get('--vars', None) != None):
            if(var_count > self.stats['--vars']):
                self.stats['--vars'] = var_count

        return 0

    #
    # Funkce slouží na parsování argumentů z příkazové řádky
    #
    def parseCmdArgs(self):
        parser = argparse.ArgumentParser(prog='python3.6 interpret.py', add_help=False, description='Interpret XML reprezentace kódu. Pro správnou funkčnost je nutná verze Python3.6.')
        parser.add_argument('--help', dest='help', action='store_true', default=False, help='nápověda')
        parser.add_argument('--source', dest='source')
        parser.add_argument('--stats', dest='stats')
        parser.add_argument('--insts', dest='insts', action='store_true', default=None)
        parser.add_argument('--vars', dest='vars', action='store_true', default=None)

        # parsování argumentů
        result = parser.parse_args()

        # validování argumentů
        self.validateCmdArgs(result)

        # --stats; order is important!
        if(result.stats != None):
            for arg in sys.argv:
                if(arg == '--insts' or arg == '--vars'):
                    self.stats[arg] = 0

        # --help
        if result.help == True:
            parser.print_help()
            sys.exit(0)

        return result

    #
    # Funkce se stará o validování argumentů (nevhodné rozmezí hodnot, nevhodné kombinace argumentů atp.)
    #
    def validateCmdArgs(self, opts):

        # chybí-li při zadání --insts či --vars parametr --stats, jedná se o chybu 10
        if opts.stats == None and (opts.insts != None or opts.vars != None):
            self.error('Chybí parametr --stats.', 10)

    #
    # Vypíše error message na standartní chybový výstup a ukončí program se specifikovaným kódem
    #
    def error(self, message, code = -1):
        print(message, file=sys.stderr)
        sys.exit(code)

if __name__ == "__main__":
    interpret = interpret()
    exit(0)
