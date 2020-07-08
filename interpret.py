#!/bin/env python3.6

import argparse, sys
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
    TYPE_NIL = 'nil'
    TYPE_FLOAT = 'float'

    #
    # Argumenty funkce
    #
    TYPE_VAR = 'var'
    TYPE_LABEL = 'label'
    TYPE_SYMB = 'symb'
    TYPE_TYPE = 'type'
    TYPE_UNSPEC = 'TYPE_UNSPEC'

    #
    # Zásobník volání
    #
    callStack = []

    jumpTo = None
    inputFile = None
    labels = {}

    #
    # Instruction order
    # <instruction order="5" opcode="XY">
    #
    instructionOrder = 1

    #
    # Index of line contains instruction of program
    #
    instructionIndex = 0

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
        preRun = True
        while self.instructionIndex <= len(root) or self.jumpTo != None:

            # nějaká instrukce chtěla skočit
            if(self.jumpTo != None):
                self.instructionIndex = self.jumpTo
                self.instructionOrder = self.jumpTo + 1
                self.jumpTo = None
                continue
            elif(self.instructionIndex == len(root)):
                if preRun:
                    preRun = False
                    self.jumpTo = 0
                    continue
                else:
                    break

            # čti instrukci
            child = root[self.instructionIndex]

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
            if preRun:
                self.executePreRunInstruction(child.get('opcode'), list(child))
            else:
                self.executeInstruction(child.get('opcode'), list(child))
            self.instructionOrder += 1
            self.instructionIndex += 1

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
    def isValidLabel(self, arg):
        if(arg.get("type") != self.TYPE_LABEL):
            return False
        if(re.match('[a-zA-Z0-9_\-$&%*]+$', arg.text) == None):
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

    def isValidBoolean(self, value):
        if(re.match('^(' + self.TYPE_BOOLEAN_TRUE + '|' + self.TYPE_BOOLEAN_FALSE + ')$', str(value)) != None):
            return True
        return False

    def isValidInteger(self, value):
        if(re.match('^[-]?[0-9]*$', str(value)) != None):
            return True
        return False

    def isValidString(self, value):
        # Speciální výjimka pro prázdný strig.
        if(not value or re.match('^.*$', str(value)) != None):
            return True
        return False

    def isValidFloat(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def isValidNil(self, value):
        if(value != self.TYPE_NIL):
            return False
        return True

    #
    # Funkce slouží pro kontrolu hodnoty konstanty předané parametrem arg dle jejího typu
    #
    def isValidConstant(self, object):

        # bool
        if(object.get("type") == self.TYPE_BOOLEAN and self.isValidBoolean(object.text)):
            return True

        # integer
        elif(object.get("type") == self.TYPE_INTEGER and self.isValidInteger(object.text)):
            return True

        # string 
        elif(object.get("type") == self.TYPE_STRING and self.isValidString(object.text)):
            return True

        # float
        elif(object.get("type") == self.TYPE_FLOAT and self.isValidFloat(object.text)):
            return True

        # nil
        elif(object.get("type") == self.TYPE_NIL and self.isValidNil(object)):
            return True

        return False

    def isValidType(self, object):
        if(re.match('^(' + self.TYPE_STRING + '|' + self.TYPE_INTEGER + '|' + self.TYPE_BOOLEAN + '|' + self.TYPE_FLOAT + self.TYPE_NIL + '){1}$', object.text) != None):
            return True
        return False

    #
    # Funkce slouží pro kontrolu symbolu předaného parametrem arg, symbol se může skládat buď z proměnné nebo konstanty
    #
    def isValidSymbol(self, object):
        return self.isValidVariable(object) or self.isValidConstant(object)

    #
    # Nahradí escape sequence označené dekadickým kódem.
    #
    # Vstup: string@řetězec\032s\032lomítkem\032\092\032a\010novým\035řádkem
    # Výstup: řetězec s lomítkem \ a
    # novým#řádkem
    def replaceEscapeDecadicSequences(self, value):

        def replace(match):
            return chr(int(match.group(1)))

        aux = str(value)
        regex = re.compile(r"\\(\d{1,3})")
        result = regex.sub(replace, aux)

        return result

    #
    # Instruction WRITE
    #
    def writeIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_SYMB])

        # získání hodnoty
        value = self.getSymbolValue(args[0])

        # nahrazení eskape sekvencí
        value = self.replaceEscapeDecadicSequences(value)

        # tisknutí hodnoty
        print(value, end="")

    #
    # Instruction EXIT
    #
    def exitIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_SYMB], [self.TYPE_INTEGER])

        try:
            value = self.getSymbolValue(args[0])
            if value < 0 or value > 49:
                raise ValueError
            sys.exit(value)
        except ValueError:
            self.error('Symbol není celé číslo v intervalu 0 až 49 (včetně)', 57)

    #
    # Instruction BREAK
    #
    def breakIns(self):
        print('Global Frame: ' + str(self.GF), file=sys.stderr)
        print('Local Frame: ' + str(self.LFStack), file=sys.stderr)
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
    def dprintIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_SYMB])

        # value
        value = self.getSymbolValue(args[0])

        # vypsání hodnoty
        print(value, file=sys.stderr)

    #
    # Instruction AND
    #
    def andIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_BOOLEAN, self.TYPE_BOOLEAN])

        # value1
        value1 = self.getSymbolValue(args[1])

        # value2
        value2 = self.getSymbolValue(args[2])

        # AND
        if value1 and value2:
            result = self.TYPE_BOOLEAN_TRUE
        else:
            result = self.TYPE_BOOLEAN_FALSE

        # uložení
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            result,
            self.TYPE_BOOLEAN
        )

    #
    # Instruction OR
    #
    def orIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_BOOLEAN, self.TYPE_BOOLEAN])

        # value1
        value1 = self.getSymbolValue(args[1])

        # value2
        value2 = self.getSymbolValue(args[2])

        # OR
        if value1 and value2:
            result = self.TYPE_BOOLEAN_TRUE
        else:
            result = self.TYPE_BOOLEAN_FALSE

        # uložení
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            result,
            self.TYPE_BOOLEAN
        )

    def getLabel(self, labelObject):

        # value
        value = self.getLabelValue(labelObject)

        # existuje návěští?
        if not value in self.labels:
            self.error('Neexistující návěští', 52)

        return self.labels[value]

    def setLabel(self, labelObj):

        # label
        label = self.getLabelValue(labelObj)

        # existuje návěští?
        if label in self.labels:
            self.error('Pokus o redefinici existujícího návěští', 52)

        # uložení
        self.labels[label] = self.instructionOrder

    #
    # Instruction LABEL
    #
    def labelIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_LABEL])

        # uložení
        self.setLabel(args[0])

    #
    # Instruction JUMP
    #
    def jumpIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_LABEL])

        # nastavení skoku
        self.jumpTo = self.getLabel(args[0])

    #
    # Instruction JUMPIFEQ
    #
    def jumpifeqIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_LABEL, self.TYPE_SYMB, self.TYPE_SYMB])

        # type1
        type1 = self.getSymbolType(args[1])

        # type2
        type2 = self.getSymbolType(args[2])

        # porovnání typů
        if type1 != type2:
            self.error('Typy se musejí rovnat', 53)

        # value1
        value1 = self.getSymbolValue(args[1])

        # value2
        value2 = self.getSymbolValue(args[2])

        # porovnání hodnot
        if value1 == value2:
            self.jumpTo = self.getLabel(args[0])

    #
    # Instruction JUMPIFNEQ
    #
    def jumpifneqIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_LABEL, self.TYPE_SYMB, self.TYPE_SYMB])

        # type1
        type1 = self.getSymbolType(args[1])

        # type2
        type2 = self.getSymbolType(args[2])

        # porovnání typů
        if type1 != type2:
            self.error('Typy se musejí rovnat', 53)

        # value1
        value1 = self.getSymbolValue(args[1])

        # value2
        value2 = self.getSymbolValue(args[2])

        # porovnání hodnot
        if value1 != value2:
            self.jumpTo = self.getLabel(args[0])

    #
    # Instruction STRI2INT
    #
    def stri2intIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_STRING, self.TYPE_INTEGER])

        # získání pozice
        position = self.getSymbolValue(args[2])

        # v řetězci
        text = self.getSymbolValue(args[1])

        try:
            # získání znaku
            char = text[position]

            # uložení řetězce
            self.setVariable(
                self.getVariableFrame(args[0]),
                self.getVariableName(args[0]),
                ord(char),
                self.TYPE_INTEGER
            )
        # pozice mimo daný řetězec vede na chybu 58
        except IndexError:
            self.error('Indexace mimo daný řetězec', 58)

    #
    # Instruction FLOAT2INT
    #
    def float2intIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_FLOAT])

        # získání hodnoty
        value = int(float(self.getSymbolValue(args[1])))

        # nastavení hodnoty
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            value,
            self.TYPE_INTEGER
        )

    #
    # Instruction NOT
    #
    def notIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_BOOLEAN])

        # value
        value = self.getSymbolValue(args[1])

        # NOT
        if value:
            result = self.TYPE_BOOLEAN_FALSE
        else:
            result = self.TYPE_BOOLEAN_TRUE

        # nastavení hodnoty
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            result,
            self.TYPE_BOOLEAN
        )

    #
    # Instruction STRLEN
    #
    def strlenIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_STRING])

        # zjištění délky
        length = len(self.getSymbolValue(args[1]))

        # uložení
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            length,
            self.TYPE_INTEGER
        )

    #
    # Instruction SETCHAR
    #
    def setcharIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_STRING, self.TYPE_INTEGER, self.TYPE_STRING])

        # získání pozice
        position = self.getSymbolValue(args[1])

        # v řetězci
        text = self.getVariable(self.getVariableFrame(args[0]), self.getVariableName(args[0])).get('value')

        # získání prvního znaku
        char = self.getSymbolValue(args[2])[0]

        try:
            # nahrazení znaku
            text[position] = char

            # uložení řetězce
            self.setVariable(
                self.getVariableFrame(args[0]),
                self.getVariableName(args[0]),
                text,
                self.TYPE_STRING
            )
        # pozice mimo daný řetězec vede na chybu 58
        except IndexError:
            self.error('Indexace mimo daný řetězec', 58)

    #
    # Instruction LT
    #
    def ltIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_BOOLEAN, self.TYPE_UNSPEC, self.TYPE_UNSPEC])

        # type1
        type1 = self.getSymbolType(args[1])

        # type2
        type2 = self.getSymbolType(args[2])

        # porovnání typů
        if type1 != type2:
            self.error('Typy se musejí rovnat', 53)

        # dodatečná kontrola typů
        if type1 == self.TYPE_NIL or type2 == self.TYPE_NIL:
            self.error('S operandem typu ' + self.TYPE_NIL + ' lze porovnávat pouze instrukcí EQ', 53)

        # value1
        value1 = self.getSymbolValue(args[1])

        # value2
        value2 = self.getSymbolValue(args[2])

        # porovnání hodnot
        if str(value1) < str(value2):
            result = self.TYPE_BOOLEAN_TRUE
        else:
            result = self.TYPE_BOOLEAN_FALSE

        # uložení výsledku
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            result,
            self.TYPE_BOOLEAN
        )


    #
    # Instruction EQ
    #
    def eqIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_BOOLEAN, self.TYPE_UNSPEC, self.TYPE_UNSPEC])

        # type1
        type1 = self.getSymbolType(args[1])

        # type2
        type2 = self.getSymbolType(args[2])

        # porovnání typů
        if type1 != type2:
            self.error('Typy se musejí rovnat', 53)

        # value1
        value1 = self.getSymbolValue(args[1])

        # value2
        value2 = self.getSymbolValue(args[2])

        # porovnání hodnot
        if str(value1) == str(value2):
            result = self.TYPE_BOOLEAN_TRUE
        else:
            result = self.TYPE_BOOLEAN_FALSE

        # uložení výsledku
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            result,
            self.TYPE_BOOLEAN
        )

    #
    # Instruction GT
    #
    def gtIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_BOOLEAN, self.TYPE_UNSPEC, self.TYPE_UNSPEC])

        # type1
        type1 = self.getSymbolType(args[1])

        # type2
        type2 = self.getSymbolType(args[2])

        # porovnání typů
        if type1 != type2:
            self.error('Typy se musejí rovnat', 53)

        # dodatečná kontrola typů
        if type1 == self.TYPE_NIL or type2 == self.TYPE_NIL:
            self.error('S operandem typu ' + self.TYPE_NIL + ' lze porovnávat pouze instrukcí EQ', 53)

        # value1
        value1 = self.getSymbolValue(args[1])

        # value2
        value2 = self.getSymbolValue(args[2])

        # porovnání hodnot
        if str(value1) > str(value2):
            result = self.TYPE_BOOLEAN_TRUE
        else:
            result = self.TYPE_BOOLEAN_FALSE

        # uložení výsledku
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            result,
            self.TYPE_BOOLEAN
        )

    #
    # Instruction GETCHAR
    #
    def getcharIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB, self.TYPE_SYMB], [self.TYPE_UNSPEC, self.TYPE_STRING, self.TYPE_INTEGER])

        # získání pozice
        position = self.getSymbolValue(args[2])

        # v textu
        text = self.getSymbolValue(args[1])

        try:
            # získání znaku
            char = text[position]

            # uložení znaku
            self.setVariable(
                self.getVariableFrame(args[0]),
                self.getVariableName(args[0]),
                char,
                self.TYPE_STRING
            )
        # pozice mimo daný řetězec vede na chybu 58
        except IndexError:
            self.error('Indexace mimo daný řetězec', 58)

    #
    # Instruction TYPE
    #
    def typeIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_SYMB])

        # zjištění typu
        type = self.getSymbolType(args[1])

        # uložení typu
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            type,
            self.TYPE_STRING
        )

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

    def getTypeValue(self, typeObj):
        return typeObj.text

    #
    # Instruction READ
    #
    def readIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR, self.TYPE_TYPE])

        # type
        type = self.getTypeValue(args[1])

        # hodnota
        value = None

        # v případě existujícího input souboru vezmeme z něj
        if(self.inputFile != None):
            try:
                value = self.inputFile.readline().rstrip()
            except:
                self.error('Nepodařilo se číst soubor pro čtení vstupu', 11)
        # jinak čekáme na zadání od uživatele
        else:
            value = input()

        # nastavení proměnné
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]),
            self.getInitialVariableValueByType(value, type),
            type
        )

    #
    # Funkce vrací hodnotu pro konstantu.
    #
    # Vstup: <arg1 type="string">světe</arg1>
    #        <arg1 type="string"></arg1>
    def getConstantValue(self, constObject):
        if(constObject.text == None):
            return ""
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
          return self.getValueByType(self.getConstantValue(symbObject), self.getConstantType(symbObject))

    def getSymbolType(self, symbObject):

        # symbol je proměnná
        if(self.isValidVariable(symbObject)):
          return self.getVariable(
              self.getVariableFrame(symbObject),
              self.getVariableName(symbObject)
          ).get('type')

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
                self.getSymbolType(symbObject)
            )
        except (IndexError):
            self.error('Datový zásobník je prázdný', 56)

    #
    # V případě chybného vstupu bude do proměnné uložena implicitní hodnota (dle typu 0, prázdný řetězec nebo false).
    #
    def getInitialVariableValueByType(self, value, type):
        if type == self.TYPE_STRING:
            try:
                value = str(value)
            except (ValueError, TypeError):
                value = ""
        if type == self.TYPE_INTEGER:
            try:
                value = int(value)
            except (ValueError, TypeError):
                value = 0
        if type == self.TYPE_BOOLEAN:
            if value.upper() == self.TYPE_BOOLEAN_TRUE.upper():
                value = self.TYPE_BOOLEAN_TRUE
            elif value.upper() == self.TYPE_BOOLEAN_FALSE.upper():
                value = self.TYPE_BOOLEAN_FALSE
            else:
                value = self.TYPE_BOOLEAN_FALSE

        return value

    #
    # V případě chybného vstupu bude do proměnné hvar i uložena implicitní hodnota (dle typu 0, prázdný řetězec
    # nebo false).
    #
    def getValueByType(self, value, type):
        if type == self.TYPE_STRING:
            return str(value)
        elif type == self.TYPE_INTEGER:
            return int(value)
        elif type == self.TYPE_BOOLEAN:
            return str(value)
        elif type == self.TYPE_NIL:
            return str(value)

        return value

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

            value = None
            if requiredArgs[requiredArgsTypeCounter] == self.TYPE_SYMB:
               value = self.getSymbolValue(argsObject[requiredArgsTypeCounter])
            elif requiredArgs[requiredArgsTypeCounter] == self.TYPE_VAR:
                value = self.getVariable(
                    self.getVariableFrame(argsObject[requiredArgsTypeCounter]),
                    self.getVariableName(argsObject[requiredArgsTypeCounter])
                ).get('value')

            if value != None:
                if(requiredArgType == self.TYPE_INTEGER):
                    if(not self.isValidInteger(value)):
                        self.error('Vyžadovaný argument ve funkci ' + opCode + ' na pozici ' + requiredArgsCounter + ' typu ' + self.TYPE_INTEGER + ' není validní', 53)
                elif(requiredArgType == self.TYPE_STRING):
                    if(not self.isValidString(value)):
                        self.error('Vyžadovaný argument ve funkci ' + opCode + ' na pozici ' + requiredArgsCounter + ' typu ' + self.TYPE_STRING + ' není validní', 53)
                elif(requiredArgType == self.TYPE_BOOLEAN):
                    if(not self.isValidBoolean(value)):
                        self.error('Vyžadovaný argument ve funkci ' + opCode + ' na pozici ' + requiredArgsCounter + ' typu ' + self.TYPE_BOOLEAN + ' není validní', 53)
                elif(requiredArgType == self.TYPE_FLOAT):
                    if(not self.isValidFloat(value)):
                       self.error('Vyžadovaný argument ve funkci ' + opCode + ' na pozici ' + requiredArgsCounter + ' typu ' + self.TYPE_FLOAT + ' není validní', 53)
                elif(requiredArgType == self.TYPE_NIL):
                    if(not self.isValidNil(value)):
                        self.error('Vyžadovaný argument ve funkci ' + opCode + ' na pozici ' + requiredArgsCounter + ' typu ' + self.TYPE_NIL + ' není validní', 53)

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

        # zkopíruje hodnotu symb do var
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0]), 
            self.getSymbolValue(args[1]),
            self.getSymbolType(args[1])
        )

    #
    # Nastavuje hodnotu a typ proměnné dle uvedeného rámce.
    # V případě varValue None nebo varType None se jedná o deklaraci
    #
    def setVariable(self, varFrame, varName, varValue = None, varType = None):

        # konverze na typ
        varValue = self.getValueByType(varValue, varType)

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

    #
    # Instruction DEFVAR
    #
    def defVarIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_VAR])

        # nastav (bez určení typu a hodnoty)
        self.setVariable(
            self.getVariableFrame(args[0]),
            self.getVariableName(args[0])
        )

    #
    # Instruction CALL
    #
    def callIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [self.TYPE_LABEL])

        # uloží inkrementovanou aktuální pozici z interního čítače instrukcí do zásobníku volání
        nextInstructionIndex = self.instructionIndex + 1
        self.callStack.append(nextInstructionIndex)

        # provede skok na zadané návěští
        self.jumpTo = self.getLabel(args[0])

    #
    # Instruction RETURN
    #
    def returnIns(self, opCode, args):

        # ověření argumentů
        self.checkInstructionArgs(opCode, args, [])

        # vyjme pozici ze zásobníku volání
        value = self.callStack.pop()

        # skočí na tuto pozici nastavením interního čítače instrukcí
        self.jumpTo = value

    #
    # Funkce obstarává zavolání pro každou instrukci zvlášť, opcode v xml buď odpovídá některé z povolených instrukcí nebo funkce skončí chybou.
    # Parametry: opcode a argumenty(args) pro danou instrukci.
    #
    def executePreRunInstruction(self, opcode, args):
        upperOpCode = opcode.upper()

        if upperOpCode == 'LABEL':
            self.labelIns(opcode, args)

    #
    # Funkce obstarává zavolání pro každou instrukci zvlášť, opcode v xml buď odpovídá některé z povolených instrukcí nebo funkce skončí chybou.
    # Parametry: opcode a argumenty(args) pro danou instrukci.
    #
    def executeInstruction(self, opcode, args):
        upperOpCode = opcode.upper()

        if(upperOpCode == 'CALL'):
            self.callIns(opcode, args)
        elif(upperOpCode == 'RETURN'):
            self.returnIns(opcode, args)
        elif(upperOpCode == 'MOVE'):
            self.moveIns(opcode, args)
        elif(upperOpCode == 'CREATEFRAME'):
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
            self.breakIns()
        elif(upperOpCode == 'POPS'):
            self.popsIns(opcode, args)
        elif(upperOpCode == 'PUSHS'):
            self.pushsIns(opcode, args)
        elif(upperOpCode == 'DEFVAR'):
            self.defVarIns(opcode, args)
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
            pass # pre run
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
            self.error('Alespoň jeden z parametrů (--source nebo --input) musí být vždy zadán', 10)

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
