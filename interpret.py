#!/bin/env python3.6

import argparse, sys
import os
import xml.etree.ElementTree as ET
import re

#
# Interpret XML reprezentace kódu
#
class interpret:


    language = 'IPPcode19'

    #
    # Globální rámec, značíme GF (Global Frame), který je na začátku interpretace automaticky inicializován
    # jako prázdný; slouží pro ukládání globálních proměnných.
    #
    GF = {}
    FRAME_GLOBAL = 'GF'

    #
    # Lokální rámec, značíme LF (Local Frame), který je na začátku nedefinován a odkazuje na vrcholový/aktuální 
    # rámec na zásobníku rámců; slouží pro ukládání lokálních proměnných funkcí (zásobník
    # rámců lze s výhodou využít při zanořeném či rekurzivním volání funkcí);
    #
    LFStack = []
    FRAME_LOCAL = 'LF'

    #
    # Dočasný rámec, značíme TF (Temporary Frame), který slouží pro chystání nového nebo úklid starého
    # rámce (např. při volání nebo dokončování funkce), jenž může být přesunut na zásobník rámců
    # a stát se aktuálním lokálním rámcem. Na začátku interpretace je dočasný rámec nedefinovaný.
    #
    TF = None
    FRAME_TEMPORARY = 'TF'

    #
    # Datové typy
    #
    TYPE_BOOLEAN = 'bool'
    TYPE_BOOLEAN_TRUE = 'true'
    TYPE_BOOLEAN_FALSE = 'false'
    TYPE_INTEGER = 'int'
    TYPE_STRING = 'string'
    TYPE_NIL = 'nil' # TODO: chybí při kontrole isTypeValid
    TYPE_FLOAT = 'float'

    #
    # Argumenty funkce
    #
    TYPE_VAR = 'var'
    TYPE_LABEL = 'label'
    TYPE_SYMB = 'symb'
    TYPE_TYPE = 'type'
    TYPE_UNSPEC = 'TYPE_UNSPEC'


    jumpTo = None
    inputFile = None
    labels = {}
    instructionOrder = 1


    #
    # Parametry pro sbírání statistik interpretace kódu. (může být --insts a --vars)
    #
    statsParameters = {}

    #
    # Datový zásobník. Operační kód zásobníkových instrukcí je zakončen písmenem „S“.
    # Zásobníkové instrukce případně načítají chybějící operandy z datového zásobníku a
    # výslednou hodnotu operace případně ukládají zpět na datový zásobník.
    #
    dataStack = []

    #
    # Datový zásobník. Operační kód zásobníkových instrukcí je zakončen písmenem „S“.
    # Zásobníkové instrukce případně načítají chybějící operandy z datového zásobníku a
    # výslednou hodnotu operace případně ukládají zpět na datový zásobník.
    #
    dataStack = []

    #
    # Konstruktor volá funkci na parsování argumentů
    # Konstruktor volá funkci run na samotnou intepretaci
    #
    def __init__(self):

        # parsování argumentů z příkazové řádky
        opts = self.parseCmdArgs()

        # interpretace
        self.run(opts)

    #
    # Funkce se volá hned po zavolání konstruktoru.
    # Funkce se stará i intepretaci kódu předaného pomocí souboru argumentem --source nebo ze standartního vstupu
    #
    def run(self, opts):

        try:
            if(opts.source != None):
                tree = ET.parse(opts.source)
                root = tree.getroot()
            else:
                try:
                    input = sys.stdin.buffer
                except AttributeError:
                    input = sys.stdin
                except:
                     self.error('Nepodařilo se načíst data ze standartního vstupu', 11)

                xmlString = input.read()
                root = ET.fromstring(xmlString)
        except ET.ParseError:
            self.error("Nevalidní formát vstupního XML", 52)

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

        # v případě existujícího input souboru se ho pokusíme otevřít
        if(opts.input != None):
            try:
                self.inputFile = open(opts.input, "r")
            except:
                self.error('Nepodařilo se otevřít soubor pro čtení vstupu: ' + opts.input,11)

        # procházení všech instrukcí
        index = 0
        while index <= len(root):

            # nějaká instrukce chtěla skočit
            if(self.jumpTo != None):
                index = self.jumpTo
                self.instructionOrder = self.jumpTo + 1
                self.jumpTo = None
            elif(index == len(root)):
                break

            # čti instrukci
            child = root[index]

            if(int(child.get('order')) != self.instructionOrder):
                self.error('Číslování instrukcí není inkrementální po 1, číslo instrukce: ' + child.get('order') + ' by mělo být: ' + str(self.instructionOrder), 31)
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
                argumentOrder += 1

            # vykonání konkrétní instrukce (zatím nevíme, jestli taková vůbec existuje, zkontrolovali jsme pouze formální stránku XML)
            self.executeInstruction(child.get('opcode'), list(child))
            self.instructionOrder+=1
            index += 1

        # interpret proběhl bez chyby, uložíme statistiky do souboru dle pořadí pokud je rozšíření aktivováno
        if(opts.stats != None):
            try:
                f = open(opts.stats, "w")
                f.truncate()
                for info in self.statsParameters:
                    f.write(str(self.statsParameters[info]) + "\n")
                f.close()
            except:
                self.error('Nepodařilo se otevřít soubor pro zápis statistik: ' + opts.stats,12)

        # v případě existujícího input souboru se ho pokusíme zavřít
        if(opts.input != None):
            try:
                self.inputFile.close()
            except:
                self.error('Nepodařilo se zavřít soubor pro čtení vstupu: ' + opts.input,11)

        sys.exit(0)

    #
    # Funkce slouží pro validování názvu pro návěští.
    #
    def isValidLabelName(self, arg):
        if(arg.get("type") != self.TYPE_LABEL):
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

    def getLabelValue(self, arg):
        return arg.text

    #
    # Funkce slouží pro kontrolu názvu proměnné předané v arg
    #
    # Identifikátor proměnné se skládá ze dvou částí oddělených
    # zavináčem (znak @; bez bílých znaků), označení rámce LF, TF nebo GF a samotného jména proměnné
    # (sekvence libovolných alfanumerický a speciálních znaků bez bílých znaků začínající písmenem nebo
    # speciálním znakem, kde speciální znaky jsou: , -, $, &, %, *). Např. GF@ x značí proměnnou x
    # uloženou v globálním rámci.
    #
    def isValidVariable(self, object):
        if(object.get("type") != self.TYPE_VAR):
            return False
        if(re.match('^(' + self.FRAME_LOCAL + '|' + self.FRAME_TEMPORARY + '|' + self.FRAME_GLOBAL + '){1}@[a-zA-Z_\-$&%*]{1}[a-zA-Z0-9_\-$&%*]*$', object.text) == None):
            return False
        return True

    def isValidBoolean(self, object):
        if(object.get("type") != self.TYPE_BOOLEAN):
            return False
        if(re.match('^(' + self.TYPE_BOOLEAN_TRUE + '|' + self.TYPE_BOOLEAN_FALSE + ')$', object.text) != None):
            return True
        return False

    def isValidInteger(self, object):
        if(object.get("type") != self.TYPE_INTEGER):
            return False
        if(re.match('^[-]?[0-9]*$', object.text) != None):
            return True
        return False

    def isValidString(self, object):
        if(object.get("type") != self.TYPE_STRING):
            return False
        # Speciální výjimka pro prázdný strig.
        if(not object.text or re.match('^.*$', object.text) != None):
            return True
        return False

    def isValidFloat(self, object):
        if(object.get("type") != self.TYPE_FLOAT):
            return False
        try:
            float(object.text)
            return True
        except ValueError:
            return False

    #
    # Funkce slouží pro kontrolu hodnoty konstanty předané parametrem arg dle jejího typu
    #
    def isValidConstant(self, object):

        # bool
        if(object.get("type") == self.TYPE_BOOLEAN and self.isValidBoolean(object)):
            return True

        # integer
        elif(object.get("type") == self.TYPE_INTEGER and self.isValidInteger(object)):
            return True

        # string 
        elif(object.get("type") == self.TYPE_STRING and self.isValidString(object)):
            return True

        # float
        elif(object.get("type") == self.TYPE_FLOAT and self.isValidFloat(object)):
            return True

        return False

    def isValidType(self, object):
        if(re.match('^(' + self.TYPE_STRING + '|' + self.TYPE_INTEGER + '|' + self.TYPE_BOOLEAN + '|' + self.TYPE_FLOAT + '){1}$', object.text) != None):
            return True
        return False

    #
    # Funkce slouží pro kontrolu symbolu předaného parametrem arg, symbol se může skládat buď z proměnné nebo konstanty
    #
    def isValidSymbol(self, object):
        return self.isValidVariable(object) or self.isValidConstant(object)

    #
    # Instruction WRITE
    #
    def writeIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_SYMB])

        # získání hodnoty
        value = self.getSymbolValue(args[0])

        # nahrazení escapovaných hodnot
        def replace(match):  # TODO: refactor
            return chr(int(match.group(1)))

        aux = str(value)
        regex = re.compile(r"\\(\d{1,3})")
        printValue = regex.sub(replace, aux)

        # tisknutí
        print(printValue, end="")

    #
    # Instruction EXIT
    #
    def exitIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_SYMB], [self.TYPE_INTEGER])

        try:
            value = int(self.getSymbolValue(args[0])) # TODO: int konverze je zbytečná?
            if value < 0 or value > 49:
                raise ValueError
            sys.exit(value)
        except ValueError:
            self.error('Symbol není celé číslo v intervalu 0 až 49 (včetně)', 57)

    #
    # Instruction BREAK
    #
    def breakIns(self, opCode, args):  # TODO:
        print('Global Frame: ' + str(self.GF), file=sys.stderr)
        print('Local Frame: ' + str(self.LF), file=sys.stderr)
        print('Temporary Frame: ' + str(self.TF), file=sys.stderr)
        if((self.statsParameters.get('--insts', None) != None)):
            print('Provedené instrukce: ' + str(self.statsParameters['--insts']), file=sys.stderr)
        if((self.statsParameters.get('--vars', None) != None)):
            print('Maximální počet inicializovaných proměnných ve všech rámcích: ' + str(self.statsParameters['--vars']), file=sys.stderr)

    #
    # Instruction ADD
    #
    def addIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_INTEGER, self.TYPE_INTEGER])

        # získání hodnot
        value1 = self.getSymbolValue(args[1])
        value2 = self.getSymbolValue(args[2])

        # spočítání
        result = value1 + value2

        # uložení
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            result,
            self.TYPE_INTEGER
        )

    #
    # Instruction MUL
    #
    def mulIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_INTEGER, self.TYPE_INTEGER])

        # získání hodnot
        value1 = self.getSymbolValue(args[1])
        value2 = self.getSymbolValue(args[2])

        # spočítání
        result = value1 * value2

        # uložení
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            result,
            self.TYPE_INTEGER
        )

    #
    # Instruction IDIV
    #
    def idivIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_INTEGER, self.TYPE_INTEGER])

        # získání hodnot
        value1 = self.getSymbolValue(args[1])
        value2 = self.getSymbolValue(args[2])

        # spočítání
        result = value1 / value2

        # uložení
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            result,
            self.TYPE_INTEGER
        )

    #
    # Instruction SUB
    #
    def subIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_INTEGER, self.TYPE_INTEGER])

        # získání hodnot
        value1 = self.getSymbolValue(args[1])
        value2 = self.getSymbolValue(args[2])

        # spočítání
        result = value1 - value2

        # uložení
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            result,
            self.TYPE_INTEGER
        )

    #
    # Instruction DPRINT
    #
    def dprintIns(self, opCode, args): # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_SYMB])

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
    def andIns(self, opCode, args): # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB])

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
    def orIns(self, opCode, args): # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB])

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
    def labelIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_LABEL])

        self.labels[self.getLabelValue(args[0])] = self.instructionOrder

    #
    # Instruction JUMP
    #
    def jumpIns(self, opCode, args):  # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_LABEL])

        self.jumpTo = self.labels[args[0].text]

    #
    # Instruction JUMPIFEQ
    #
    def jumpifeqIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_LABEL, self.TYPE_SYMB, self.TYPE_SYMB])

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
    def jumpifneqIns(self, opCode, args):  # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_LABEL, self.TYPE_VAR, self.TYPE_SYMB])

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
    def stri2intIns(self, opCode, args):  # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_VAR, self.TYPE_SYMB])

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
    # Instruction FLOAT2INT
    #
    def float2intIns(self, opCode, args):  # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB])

        intvalue = 0
        if(self.isValidVar(args[1]) == False):
            if(args[1].get("type") != 'float'):
                self.error('Symbol není float', 53)
            try:
                intvalue = int(float(args[1].text))
            except:
                self.error('Není validní hodnota', 58)
        else:
            if(self.GF.get(self.getSymbValue(args[1])).get("type") != "float"):
                self.error('Symbol není float', 53)

            try:
                intvalue = int(float(self.GF.get(self.getSymbValue(args[1])).get("value")))
            except:
                self.error('Není validní hodnota', 58)

        # uložení hodnoty int
        self.GF[self.getSymbValue(args[0])] = {"value": intvalue, "type": "int"}

    #
    # Instruction NOT
    #
    def notIns(self, opCode, args): # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_VAR])

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
    def strlenIns(self, opCode, args):  # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_VAR])

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
    def setcharIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_STRING, self.TYPE_INTEGER, self.TYPE_STRING])

        # získání pozice
        position = int(self.getSymbolValue(args[1]))

        text = self.getVariable(self.getVariableFrame(args[0]), self.getVariableName(args[0])).get('value')

        # pozice mimo daný řetězec vede na chybu 58
        if (position >= len(text) or (position < 0)):
            self.error('Indexace mimo daný řetězec', 58)

        # získání prvního znaku
        char = self.getSymbolValue(args[2])[0]

        text[position] = char

        # nahrazení znaku
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            text,
            self.getVariableType(args[0])
        )

    #
    # Instruction LT
    #
    def ltIns(self, opCode, args):  # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_VAR, self.TYPE_SYMB])

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
    def eqIns(self, opCode, args):  # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_VAR, self.TYPE_SYMB])

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
    def gtIns(self, opCode, args):  # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_VAR, self.TYPE_SYMB])

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
    def getcharIns(self, opCode, args):  # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_STRING, self.TYPE_INTEGER])

        # získání pozice
        position = int(self.getSymbolValue(args[2]))

        # v textu
        text = self.getSymbolValue(args[1])

        # pozice mimo daný řetězec vede na chybu 58
        if (position >= len(text) or (position < 0)):
            self.error('Indexace mimo daný řetězec', 58)

        # získání znaku
        char = text[position]

        # uložení znaku
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            char,
            self.TYPE_STRING
        )

    #
    # Instruction TYPE
    #
    def typeIns(self, opCode, args):  # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_VAR, self.TYPE_SYMB])

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
    # Instruction CONCAT
    #
    def concatIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_STRING, self.TYPE_STRING])

        # value1
        value1 = self.getSymbolValue(args[1])

        # value2
        value2 = self.getSymbolValue(args[2])

        # konkatenace
        result = value1 + value2

        # nastavení hodnoty
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            result,
            self.TYPE_STRING
        )

    #
    # Instruction INT2CHAR
    #
    def int2charIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB])

        try:
            # získání znaku
            char = chr(int(self.getSymbolValue(args[1])))

            # nastavení hodnoty
            self.setVariable(
                self.getVariableFrame(args[0]),
                self.getVariableName(args[0]),
                char,
                self.TYPE_STRING
            )
        # Není-li symb validní ordinální hodnota znaku v Unicode dojde k chybě 58.
        except (ValueError):
            self.error('Není validní ordinální hodnota znaku v Unicode', 58)

    #
    # Instruction INT2FLOAT
    #
    def int2floatIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_INTEGER])

        # získání hodnoty
        value = float(int(self.getSymbolValue(args[1])))

        # nastavení hodnoty
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            value,
            self.TYPE_FLOAT
        )

    def valueByType(self, value, type): # TODO: naimplementovat při ukládání proměnné

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
            elif(value.upper() == "FALSE"):
                value = "false"
            else:
                value = "false"

        return value

    #
    # Instruction READ
    #
    def readIns(self, opCode, args):  # TODO:

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_TYPE])

        type = args[1].text

        # v případě existujícího input souboru vezmeme z něj
        if(self.inputFile != None):
            try:
                value = self.inputFile.readline().rstrip()
            except:
                self.error('Nepodařilo se číst soubor pro čtení vstupu', 11)
        else:
            value = input()

        # nastavení hodnoty
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            value,
            type
        )

    #
    # Funkce vrací hodnotu pro konstantu.
    #
    # Vstup: <arg1 type="string">světe</arg1>
    def getConstantValue(self, constObject):
        return constObject.text
    def getConstantType(self, constObject):
        return constObject.get('type')

    #
    # Funkce vrátí hodnotu pro symbol.
    #
    # Vstup: <arg1 type="var">GF@val</arg1>
    #        <arg1 type="string">světe</arg1>
    #
    def getSymbolValue(self, symbObject):

        # symbol je proměnná
        if(self.isValidVariable(symbObject)):
          return self.getVariable(
              self.getVariableFrame(symbObject),
              self.getVariableName(symbObject)
          ).get('value')

        # symbol je konstanta
        elif(self.isValidConstant(symbObject)):
          return self.getConstantValue(symbObject)

    def getSymbolType(self, symbObject):

        # symbol je proměnná
        if(self.isValidVariable(symbObject)):
          return self.getVariableType(symbObject)

        # symbol je konstanta
        elif(self.isValidConstant(symbObject)):
          return self.getConstantType(symbObject)

    #
    # Instruction PUSHS
    #
    def pushsIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_SYMB])

        # přidání hodnoty na vrchol zásobníku
        self.dataStack.append(args[0])

    #
    # Instruction POPS
    #
    def popsIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR])

        # vytáhnutí hodnoty z vrcholu zásobníku
        # zásobník nesmí být prázdný
        try:
            symbObject = self.dataStack.pop()

            # nastavení hodnoty do proměnné
            self.setVariable(
                self.getVariableFrame(args[0]),
                self.getVariableName(args[0]),
                self.getSymbolValue(symbObject),
                self.getVariableTypeFromValue(symbObject)
            )
        except (IndexError):
            self.error('Datový zásobník je prázdný', 56)

    def getVariableTypeFromValue(self, object):
        if(self.isValidInteger(object)):
            return self.TYPE_INTEGER 
        elif(self.isValidBoolean(object)):
            return self.TYPE_BOOLEAN
        elif(self.isValidType(object)):
            return self.TYPE_TYPE
        elif(self.isValidFloat(object)):
            return self.TYPE_FLOAT
        elif(self.isValidString(object)):
            return self.TYPE_STRING
        elif(self.isValidVariable(object)):
            return self.TYPE_VAR


    #
    # Funkce kontroluje argumenty instrukce.
    #
    def checkInstructionArgs(self, opCode, argsObject, requiredArgs, requiredArgsType = []):
        if(len(requiredArgs) != len(argsObject)):
            self.error('U instrukce ' + opCode + ' musí být počet argumentů roven ' + len(requiredArgs), 52)

        requiredArgsCounter = 0
        for requiredArg in requiredArgs:
             if(requiredArg == self.TYPE_VAR):
                if(not self.isValidVariable(argsObject[requiredArgsCounter])):
                    self.error('Vyžadovaný argument ve funkci ' + opCode + ' na pozici ' + requiredArgsCounter + ' typu proměnná (var) není validní', 53)
             elif(requiredArg == self.TYPE_SYMB):
                if(not self.isValidSymbol(argsObject[requiredArgsCounter])):
                    self.error('Vyžadovaný argument ve funkci ' + opCode + ' na pozici ' + requiredArgsCounter + ' typu symbol (var, const) není validní', 53)
             elif(requiredArg == self.TYPE_LABEL):
                if(not self.isValidLabel(argsObject[requiredArgsCounter])):
                    self.error('Vyžadovaný argument ve funkci ' + opCode + ' na pozici ' + requiredArgsCounter + ' typu návěští (label) není validní', 53)
             elif(requiredArg == self.TYPE_TYPE):
                if(not self.isValidType(argsObject[requiredArgsCounter])):
                    self.error('Vyžadovaný argument ve funkci ' + opCode + ' na pozici ' + requiredArgsCounter + ' typu typ (type) není validní', 53)

             requiredArgsCounter+=1

        requiredArgsTypeCounter = 0
        for requiredArgType in requiredArgsType:
             if(requiredArgType == self.TYPE_INTEGER):
                if(not self.isValidInteger(argsObject[requiredArgsTypeCounter])):
                    self.error('Vyžadovaný argument ve funkci ' + opCode + ' na pozici ' + requiredArgsCounter + ' typu ' + self.TYPE_INTEGER + ' není validní', 53)
             if(requiredArgType == self.TYPE_STRING):
                if(not self.isValidString(argsObject[requiredArgsTypeCounter])):
                    self.error('Vyžadovaný argument ve funkci ' + opCode + ' na pozici ' + requiredArgsCounter + ' typu ' + self.TYPE_STRING + ' není validní', 53)
             if(requiredArgType == self.TYPE_BOOLEAN):
                if(not self.isValidBoolean(argsObject[requiredArgsTypeCounter])):
                    self.error('Vyžadovaný argument ve funkci ' + opCode + ' na pozici ' + requiredArgsCounter + ' typu ' + self.TYPE_BOOLEAN + ' není validní', 53)

             requiredArgsTypeCounter+=1

        return True

    #
    # Instruction CREATEFRAME
    #
    def createFrameIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [])

        # vytvoří nový dočasný rámec a zahodí případný obsah původního dočasného rámce
        self.TF = {}

    #
    # Instruction PUSHFRAME
    #
    def pushFrameIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [])

        # dočasný rámec k přesunutí musí existovat
        if(self.TF is None):
            self.error('Pokus o přístup k nedefinovanému dočasnému rámci', 53)

        # přesun TF na zásobník rámců
        self.LFStack.append(self.TF)

        # dočasný rámec je po přesunutí nedefinován
        self.TF = None

    #
    # Instruction MOVE
    #
    def moveIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB])

        # hodnota symb
        value = self.getSymbolValue(args[1])

        # zkopíruje hodnotu symb do var
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]), 
            value,
            self.getVariableTypeFromValue(value)
        )

    #
    # Nastavuje hodnotu a typ proměnné dle uvedeného rámce.
    # V případě varValue None nebo varType None se jedná o deklaraci
    #
    def setVariable(self, varFrame, varName, varValue, varType):

        # globální rámec
        if(varFrame == self.FRAME_GLOBAL):

            # automaticky inicializován na začátku interpretace, kontroluju tedy pouze zda proměnná existuje pokud se nejedná o deklaraci
            if(varValue != None or varType != None):
                if(varName not in self.GF):
                    self.error('Proměnná:' + varName + ' na GF neexistuje', 54)

            # nastav
            self.GF[varName] = {"value": varValue, "type": varType}
 
        # lokální rámec
        elif(varFrame == self.FRAME_LOCAL):

            # zásobník rámců musí obsahovat alespoň 1 lokální rámec
            if(len(self.LFStack) == 0):
                self.error('Zásobník rámců je prázdný, žádný lokální rámec není v aktuální chvíli definovaný', 55)

            currentLFStack = len(self.LFStack) - 1

            # kontrola zda proměnná existuje pokud se nejedná o deklaraci
            if(varValue != None or varType != None):
                if(varName not in self.LFStack[currentLFStack]):
                    self.error('Proměnná:' + varName + ' na aktuálním LF neexistuje', 54)

            # nastav
            self.LFStack[currentLFStack][varName] = {'value': varValue, 'type': varType}

        # dočasný rámec
        elif(varFrame == self.FRAME_TEMPORARY):

            # dočasný rámec musí existovat
            if(self.TF == None):
                self.error('Dočasný rámec je nedefinovaný', 55)

            # kontrola zda proměnná existuje pokud se nejedná o deklaraci
            if(varValue != None or varType != None):
                if(varName not in self.TF):
                    self.error('Proměnná:' + varName + ' na TF neexistuje', 54)

            # nastav
            self.TF[varName] = {'value': varValue, 'type': varType}

    #
    # Vrací hodnotu proměnné dle uvedeného rámce.
    #
    # Výstup: {'value': X, 'type': Y}
    #
    def getVariable(self, varFrame, varName):

         # globální rámec
        if(varFrame == self.FRAME_GLOBAL):

            # globální rámec je automaticky inicializován na začátku interpretace, stačí kontrolovat zda proměnná existuje
            if(varName not in self.GF):
                self.error('Proměnná:' + varName + ' na GF neexistuje', 54)

            # vrať
            return self.GF[varName]

        # lokální rámec
        elif(varFrame == self.FRAME_LOCAL):

            # zásobník rámců musí obsahovat alespoň 1 lokální rámec
            if(len(self.LFStack) == 0):
                self.error('Zásobník rámců je prázdný, žádný lokální rámec není v aktuální chvíli definovaný', 55)

            currentLFStack = len(self.LFStack) - 1
            if(varName not in self.LFStack[currentLFStack]):
                self.error('Proměnná:' + varName + ' na GF neexistuje', 54)

            # vrať
            return self.LFStack[currentLFStack][varName]

        # dočasný rámec
        elif(varFrame == self.FRAME_TEMPORARY):

            # dočasný rámec musí existovat
            if(self.TF == None):
                self.error('Dočasný rámec je nedefinovaný', 55)

            # neexistuje proměnná
            if(varName not in self.TF):
                self.error('Proměnná:' + varName + ' na TF neexistuje', 54)

            # vrať
            return self.TF[varName]

    def getVariableFrame(self, arg):
        return arg.text.split("@")[0]

    def getVariableName(self, arg):
        return arg.text.split("@")[1]

    def getVariableType(self, arg):
        return arg.get('type')

    #
    # Instruction DEFVAR
    #
    def defVarIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR])

        # nastav (bez určení typu a hodnoty)
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            None,
            None
        )

    #
    # Funkce obstarává zavolání pro každou instrukci zvlášť, opcode v xml buď odpovídá některé z povolených instrukcí nebo funkce skončí chybou.
    # Parametry: opcode a argumenty(args) pro danou instrukci.
    #
    def executeInstruction(self, opcode, args):
        upperOpCode = opcode.upper()

        #'RETURN':  # TODO:
        #'CALL':  # TODO:
        if(upperOpCode == 'MOVE'):
            self.moveIns(opcode, args)
        if(upperOpCode == 'CREATEFRAME'):
            self.createFrameIns(opcode, args)
        elif(upperOpCode == 'PUSHFRAME'):
            self.pushFrameIns(opcode, args)
        elif(upperOpCode == 'INT2CHAR'):
            self.int2charIns(opcode, args)
        elif(upperOpCode == 'INT2FLOAT'):
            self.int2floatIns(opcode, args)
        elif(upperOpCode == 'FLOAT2INT'):
            self.float2intIns(opcode, args)
        elif(upperOpCode == 'BREAK'):
            self.breakIns(opcode, args)
        elif(upperOpCode == 'POPS'):
            self.popsIns(opcode, args)
        elif(upperOpCode == 'PUSHS'):
            self.pushsIns(opcode, args)
        elif(upperOpCode == 'DEFVAR'):
            self.defVarIns(opcode, args)
        elif(upperOpCode == 'BREAK'):
            self.breakIns(opcode, args)
        elif(upperOpCode == 'WRITE'):
            self.writeIns(opcode, args)
        elif(upperOpCode == 'DPRINT'):
            self.dprintIns(opcode, args)
        elif(upperOpCode == 'ADD'):
            self.addIns(opcode, args)
        elif(upperOpCode == 'SUB'):
            self.subIns(opcode, args)
        elif(upperOpCode == 'MUL'):
            self.mulIns(opcode, args)
        elif(upperOpCode == 'IDIV'):
            self.idivIns(opcode, args)
        elif(upperOpCode == 'LT'):
            self.ltIns(opcode, args)
        elif(upperOpCode == 'EQ'):
            self.eqIns(opcode, args)
        elif(upperOpCode == 'GT'):
            self.gtIns(opcode, args)
        elif(upperOpCode == 'AND'):
            self.andIns(opcode, args)
        elif(upperOpCode == 'OR'):
            self.orIns(opcode, args)
        elif(upperOpCode == 'NOT'):
            self.notIns(opcode, args)
        elif(upperOpCode == 'STRI2INT'):
            self.stri2intIns(opcode, args)
        elif(upperOpCode == 'CONCAT'):
            self.concatIns(opcode, args)
        elif(upperOpCode == 'GETCHAR'):
            self.getcharIns(opcode, args)
        elif(upperOpCode == 'SETCHAR'):
            self.setcharIns(opcode, args)
        elif(upperOpCode == 'READ'):
            self.readIns(opcode, args)
        elif(upperOpCode == 'STRLEN'):
            self.strlenIns(opcode, args)
        elif(upperOpCode == 'TYPE'):
            self.typeIns(opcode, args)
        elif(upperOpCode == 'LABEL'):
            self.labelIns(opcode, args)
        elif(upperOpCode == 'JUMP'):
            self.jumpIns(opcode, args)
        elif(upperOpCode == 'JUMPIFEQ'):
            self.jumpifeqIns(opcode, args)
        elif(upperOpCode == 'JUMPIFNEQ'):
            self.jumpifneqIns(opcode, args)
        elif(upperOpCode == 'EXIT'):
            self.exitIns(opcode, args)

        # neznámý operační kód
        else:
            self.error('Instrukce: ' + opcode.upper() + ' neexistuje', 32)

        # instrukci se podařilo provést bez erroru, inkrementujeme provedené instrukce
        if(self.statsParameters.get('--insts', None) != None):
            self.statsParameters['--insts'] += 1

        # projde všechny rámce a sečte proměnné, které jsou inicializované
        if(self.statsParameters.get('--vars', None) != None):

            # pokud je to víc než je zatím uloženo, přepíše hodnotu
            count = self.getTotalCountOfInitializedVariables()
            if(count > self.statsParameters['--vars']):
                self.statsParameters['--vars'] = count

        return 0

    #
    # Vrátí celkový počet inicializovaných proměnných ze všech aktuálně existujících rámců
    #
    def getTotalCountOfInitializedVariables(self):

        # globální rámec
        count = 0
        for GFVariableName in self.GF:
            if(self.GF[GFVariableName].get("value") != None):
                count += 1

        # projde všechny lokální rámce
        if(self.LFStack != None):
            for LF in self.LFStack:
                for LFVariableName in LF:
                    if(self.LFStack[LF][LFVariableName].get("value") != None):
                        count += 1

        # dočasný rámec
        if(self.TF != None):
            for TFVariableName in self.TF:
                if(self.TF[TFVariableName].get("value") != None):
                    count += 1

        return count

    #
    # Funkce slouží na parsování argumentů z příkazové řádky
    #
    def parseCmdArgs(self):
        argparser = argparse.ArgumentParser(prog='python3.6 interpret.py', add_help=False, description='Interpret XML reprezentace kódu ' + self.language + '. Pro správnou funkčnost je nutná verze Python3.6.')
        argparser.add_argument('--help', dest='help', action='store_true', default=False, help='Nápověda.')
        argparser.add_argument('--source', dest='source', default=None, help='Vstupní soubor s XML reprezentací zdrojového kódu dle definice ze sekce.')
        argparser.add_argument('--input', dest='input', default=None, help='Soubor se vstupy pro samotnou interpretaci zadaného zdrojového kódu.')
        argparser.add_argument('--stats', dest='stats', default=None, help='Sbírání statistik interpretace kódu. Podpora parametru --insts pro výpis počtu vykonaných instrukcí během interpretace do statistik.Podpora parametru --vars pro výpis maximálního počtu inicializovaných proměnných přítomných ve všech platných rámcích během interpretace zadaného programu do statistik.')
        argparser.add_argument('--insts', dest='insts', action='store_true', default=None)
        argparser.add_argument('--vars', dest='vars', action='store_true', default=None)

        # parsování argumentů
        result = argparser.parse_args()

        # nápověda
        if result.help == True:
            argparser.print_help()
            sys.exit(0)

        # validování argumentů
        self.validateCmdArgs(result)

        # rozšíření --stats
        self.parseExtensionStatsParameters(result)

        return result

    #
    # Funkce se stará o parsování argumentů pro rozšíření --stats (záleží na pořadí)
    #
    def parseExtensionStatsParameters(self, opts):
        if(opts.stats != None):
            for arg in sys.argv:
                if(arg == '--insts' or arg == '--vars'):
                    self.statsParameters[arg] = 0

    #
    # Funkce se stará o validování argumentů (nevhodné rozmezí hodnot, nevhodné kombinace argumentů atp.)
    #
    def validateCmdArgs(self, opts): 

        # alespoň jeden z parametrů (--source nebo --input) musí být vždy zadán
        # pokud jeden z nich chybí, tak jsou odpovídající data načítána ze standardního vstupu.
        if(opts.source == None and opts.input == None):
            self.error('Alespoň jeden z parametrů (--source nebo --input) musí být vždy zadán', 10);

        # chybí-li při zadání --stats --insts či --vars parametr, jedná se o chybu 10
        if opts.stats != None and opts.insts == None and opts.vars == None:
            self.error('Zadaný parametr --stats vyžaduje alespoň jeden z parametrů --insts (pro počítání instrukcí) či parametr --vars (pro počítání maximálního počtu inicializovaných proměnných).', 10)

        # chybí-li při zadání --insts či --vars parametr --stats, jedná se také o chybu 10
        if (opts.insts != None or opts.vars != None) and opts.stats == None:
            self.error('Zadaný parametr --stats vyžaduje alespoň jeden z parametrů --insts (pro počítání instrukcí) či parametr --vars (pro počítání maximálního počtu inicializovaných proměnných).', 10)

    #
    # Vypíše error message na standartní chybový výstup a ukončí program se specifikovaným kódem
    #
    def error(self, message, code = -1):
        print(message, file=sys.stderr)
        sys.exit(code)

if __name__ == "__main__":
    interpret = interpret()
    exit(0)
