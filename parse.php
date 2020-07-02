<?php

$parser = new Parser($argv);
$result = $parser->run();
exit($result);

/**
 * Analyzátor kódu v IPPcode19.
 */
class Parser {

  private $xmlVersion = '1.0';
  private $xmlEncoding = 'UTF-8';
  private $xmlRootName = 'program';

  private $language = 'IPPcode19';

  // soubor pro zápis statistik statsOpts při aktivovaném rozšířením STATP do souboru statsFile
  private $statsFile = null;
  private $statsOpts = array();

  // argumenty z příkazové řádky
  private $argvs = array();

  // vypíše do statistik počet řádků, na kterých se vyskytoval komentář
  private $commentsCount = 0;

  // nepočítají se prázdné řádky, ani řádky obsahující pouze komentář, ani úvodní řádek
  private $codeLinesCount = 0;

  // vypíše do statistik počet definovaných návěští (tj. unikátních možných cílů skoku)
  private $labelsCount = 0;

  // vypíše do statistik počet instrukcí pro podmíněné a nepodmíněné skoky dohromady
  private $jumpsCount = 0;

  private $instructios = array();

  // typy argumentů u funkce
  const INS_ARG_TYPE = 'type';
  const INS_ARG_SYMB = 'symb';
  const INS_ARG_VAR = 'var';
  const INS_ARG_LABEL = 'label';

  const HELP_MESSAGE = "Analyzátor kódu v IPPcode19:
      --help vypíše na standardní výstup nápovědu skriptu (nenačítá žádný vstup)
      --stats=file slouží pro zadání souboru file, kam se agregované statistiky
      budou vypisovat (po řádcích dle pořadí v dalších parametrech)
      --loc vypíše do statistik počet řádků s instrukcemi (nepočítají se prázdné
       řádky, ani řádky obsahující pouze komentář, ani úvodní řádek)
      --comments vypíše do statistik počet řádků, na kterých se vyskytoval
      komentář
      --labels vypíše do statistik počet definovaných návěští
      --jumps vypíše do statistik počet instrukcí pro podmíněné a nepodmíněné skoky dohromady\n";

  /**
   * Konstruktor přijímající argumenty uvedené v příkazové řádce.
   */
  function __construct($argvs) {
    $this->argvs = $argvs;
  }

  /**
   * Funkce se volá hned po zavolání konstruktoru.
   * Funkce poté volá funkci na parsování argumentů.
   * Funkce poté volá funkci na parsování samotného kódu v jazyce IPPcode19 daného na vstupu.
   * Funkce poté volá funkci writeStats pokud je rozšíření vyžadováno a tedy chceme statistiky o kódu sbírat do uvedeného souboru.
   * Funkce zavolá funkci writeHtml a končí.
   */
  function run() {
    $result = $this->parseArgs();
    if($result != 0) {
      return $result;
    }

    $result = $this->parseLanguage();
    if($result != 0) {
      return $result;
    }

    if($this->statsFile != null) {
      $result = $this->writeStats();
      if($result != 0) {
        return $result;
      }
    }

    $result = $this->writeXml();
    if($result != 0) {
      return $result;
    }

    return 0;
  }

  /**
   * Funkce slouží pro rozšíření STATP kdy do uvedeného souboru zapisuje statistiky o kódu.
   */
  function writeStats() {
    // soubor pro zapsání statistik
    $file = fopen($this->statsFile, "w");

    // chyba při otevření výstupních souborů pro zápis (např. nedostatečné oprávnění).
    if(!$file) {
        return 12;
    }

    // smazat předchozí obsah souboru
    file_put_contents($this->statsFile, "");

    // zapsat statistiky
    foreach($this->statsOpts as $key => $value) {
      if($key == 'loc') {
        file_put_contents($this->statsFile, $this->codeLinesCount . "\n", FILE_APPEND);
      }
      if($key == 'comments') {
        file_put_contents($this->statsFile, $this->commentsCount . "\n", FILE_APPEND);
      }
      if($key == 'labels') {
        file_put_contents($this->statsFile, $this->labelsCount . "\n", FILE_APPEND);
      }
      if($key == 'jumps') {
        file_put_contents($this->statsFile, $this->jumpsCount . "\n", FILE_APPEND);
      }
    }

    return 0;
  }

  /**
   * Funkce slouží pro kontrolu názvu proměnné předané parametrem $name.
   *
   * Identifikátor proměnné se skládá ze dvou částí oddělených
   * zavináčem (znak @; bez bílých znaků), označení rámce LF, TF nebo GF a samotného jména proměnné
   * (sekvence libovolných alfanumerický a speciálních znaků bez bílých znaků začínající písmenem nebo
   * speciálním znakem, kde speciální znaky jsou: , -, $, &, %, *). Např. GF@ x značí proměnnou x
   * uloženou v globálním rámci.
   */
  function isCorrectVarName($name) {
    if(!preg_match('/^(LF|TF|GF){1}@[a-zA-Z_\-$&%*?!]{1}[a-zA-Z0-9_\-$&%*?!]*$/', $name)) {
      return false;
    }
    return true;
  }

  /**
   * Funkce slouží pro kontrolu názvu konstanty předané parametrem $name.
   */
  function isCorrectConstant($name) {
    $bool = false;
    if(preg_match('/^bool@(true|false)$/', $name)) {
      $bool = true;
    }
    $int = false;
    if(preg_match('/^int@[-]?[0-9]*$/', $name)) {
      $int = true;
    }
    $string = false;
    if(preg_match('/^string@.*$/', $name)) {
      $string = true;
    }
    $nil = false;
    if(preg_match('/^nil@nil$/', $name)) {
      $nil = true;
    }

    if($string || $int || $bool || $nil) {
      return true;
    }

    return false;
  }

  /*
   * U literálů typu string při zápisu do XML nepřevádějte původní escape sekvence, ale
   * pouze pro problematické znaky v XML (např. <, >, &) využijte odpovídající XML entity (např.
   * &lt;, &gt;, &amp;).Podobně převádějte problematické znaky vyskytující se v identifikátorech proměnných.
   *
   * XMLWritter převádí uvedené speciální znaky automaticky ve funkci text() až na výjimku &apos. Proto je níže při zápisu použitá funkce textRaw(), aby nedošlo k opětovnému nahrazení &.
   *
   * Vstup funkce: WRITE string@\032<not-tag/>\032'.." # řetězec převádíme, aby byl správně uložen do XML elementu
   * Výstup funkce: <arg1 type="string">\032&lt;not-tag/&gt;\032&apos;..&quot;</arg1>
   */
  function replaceSelectedSpecialCharacters($string) {
    $patterns = array('/&(?!amp;)/', '/</', '/>/', "/'/", '/"/');
    $replacements = array('&amp;', '&lt;', '&gt;', '&apos;', '&quot;');

    $result = preg_replace($patterns, $replacements, $string);

    return $result;
  }

  function getConstantValue($type, $value) {
    if ($type == 'string')
      return $this->replaceSelectedSpecialCharacters($value);
    return $value;
  }

  function getVarName($name) {
    return $this->replaceSelectedSpecialCharacters($name);
  }

  /**
   * Funkce slouží pro kontrolu názvu symbolu předané parametrem $name. Symbol se může skládat buď z proměnné nebo konstanty.
   */
  function isCorrectSymbName($name) {
    return ($this->isCorrectVarName($name) || $this->isCorrectConstant($name));
  }

  /**
   * Funkce slouží pro kontrolu názvu návěstí předané parametrem $name.
   */
  function isCorrectLabelName($name) {
    if(!preg_match('/[a-z0-9_\-$&%*]+$/i', $name)) {
      return false;
    }
    return true;
  }

  /**
   * Funkce kontroluje, zda je zadaný type symbolu správný, jestliže platí Type ∈ {int, string, bool} vrací true, pakliže ne, false.
   */
  function isCorrectTypeName($name) {
    return ($name == 'bool' || $name == 'string' || $name == 'int' || $name == 'nil');
  }

  /**
   * Funkce slouží pro rozdělení symbolu podle zavináče a vrací Type. Type@Value. Pokud nejde o konstantu ale o proměnnou vrací var.
   */
  function getSymbType($name) {
    if($this->isCorrectTypeName(explode("@", $name)[0]))
        return explode("@", $name)[0];
    else
        return 'var';
  }

  /**
   * Funkce slouží pro rozpoznání zda jde o konstantu nebo proměnnou. V případě proměnné vrací $name a v případě konstanty Value za zavináčem. Type@Value.
   */
  function getSymbValue($name) {
    return $this->getSymbType($name) == 'var' ? $name : $this->getConstantValue(explode("@", $name)[0], explode("@", $name)[1]);
  }

  /**
   * Funkce se stará o parsování samotného jazyka.
   * Funkce dovoluje mezery před a po instrukcích na jednotlivých řádcích.
   * Funkce počítá komentáře/řádky s intrukcemi.
   * Funkce komentáře před kontrolou jednotlivých instrukcí odstraňuje a dále s nimi nepracuje.
   */
  function parseLanguage() {

    // standard input
    $stdin = fopen('php://stdin', 'r');

    // chyba při otevírání vstupních souborů (např. neexistence, nedostatečné oprávnění).
    if(!$stdin) {
      return 11;
    }

    // first line
    $line = fgets($stdin);
    $line = trim($line, " \r\n");

    // je i zde na prvním řádku komentář?
    if(preg_match('/\#/', $line)) {
      $this->commentsCount++;

      // pokud ano, zajímá nás pouze část před ním
      $line = explode("#", $line)[0];
    }

    // odstranit konce řádků, mezery ze začátku i konce, nezajímají nás
    $line = trim($line, " \r\n");

    // Kód v jazyce IPPcode19 začíná úvodním řádkem s tečkou následovanou jménem jazyka (nezáleží na velikosti písmen):
    if(strcmp(strtolower($line), strtolower('.' . $this->language)) !== 0) {
      return 21;
    }

    while($line = fgets($stdin)) {

      echo $line;

      // je zde komentář?
      if(preg_match('/\#/', $line)) {
        $this->commentsCount++;

        // pokud ano, zajímá nás pouze část před ním
        $line = explode("#", $line)[0];
      }

      // odstranit konce řádků, mezery ze začátku i konce, nezajímají nás
      $line = trim($line, " \r\n");

      // rozlož na jednotlivé intrukce dle mezer
      $exploded = explode(" ", $line);

      // pokud na řádku něco je, musí to být nějaká z instrukcí
      if($exploded[0]) {
        $this->codeLinesCount++;

        // název instrukce
        $ins = strtoupper($exploded[0]);

        // argumenty funkce, odstraníme název funkce a reindexujeme
        $args = $exploded;
        unset($args[0]);
        $args = array_values($args);

        switch($ins) {
          case "MOVE":
          case "INT2TOCHAR":
          case "NOT":
            $this->ins($ins, $args, array(Parser::INS_ARG_VAR, Parser::INS_ARG_SYMB));
            break;
          case "CREATEFRAME":
          case "PUSHFRAME":
          case "POPFRAME":
          case "RETURN":
          case "BREAK":
            $this->ins($ins, $args);
            break;
          case "POPS":
          case "DEFVAR":
            $this->ins($ins, $args, array(Parser::INS_ARG_VAR));
            break;
          case "CALL":
            $this->jumpsCount++;
            $this->ins($ins, $args, array(Parser::INS_ARG_LABEL));
            break;
          case "PUSHS":
          case "WRITE":
          case "EXIT":
          case "DPRINT":
            $this->ins($ins, $args, array(Parser::INS_ARG_SYMB));
            break;
          case "ADD":
          case "SUB":
          case "MUL":
          case "IDIV":
          case "LT":
          case "GT":
          case "EQ":
          case "AND":
          case "OR":
          case "STRI2INT":
          case "CONCAT":
          case "GETCHAR":
          case "SETCHAR":
            $this->ins($ins, $args, array(Parser::INS_ARG_VAR, Parser::INS_ARG_SYMB, Parser::INS_ARG_SYMB));
            break;
          case "READ":
            //$this->insVarType($ins, $args);
            $this->ins($ins, $args, array(Parser::INS_ARG_VAR));
            break;
          case "STRLEN":
          case "TYPE":
            $this->ins($ins, $args, array(Parser::INS_ARG_VAR, Parser::INS_ARG_SYMB, Parser::INS_ARG_SYMB));
            break;
          case "LABEL":
            $this->labelsCount++;
            $this->insLabel($ins, $args);
            $this->ins($ins, $args, array(Parser::INS_ARG_LABEL));
            break;
          case "JUMP":
            $this->jumpsCount++;
            $this->ins($ins, $args, array(Parser::INS_ARG_LABEL));
            break;
          case "JUMPIFEQ":
          case "JUMPIFNEQ":
            $this->jumpsCount++;
            $this->ins($ins, $args, array(Parser::INS_ARG_SYMB, Parser::INS_ARG_SYMB));
            break;
          default:
            // neznámý nebo chybný operační kód ve zdrojovém kódu zapsaném v IPPcode19
            return 22;
        }
      }
    }

    return 0;
  }

  /*
   * Funkce se stará o ověření argumentů. Kontroluje se správné pořadí, celkový počet i konkrétní typy (var, symbol, label, type)
   */
  function ins($name, $args, $requiredArgs = array()) {

    // počet parametrů nesedí
    if(count($requiredArgs) != count($args)) {
      return 23;
    }

    $argsCounter = 0;
    $argsXml = array();
    foreach($requiredArgs as $requiredArg) {
      $arg = $args[$argsCounter];
      switch($requiredArg) {
        case Parser::INS_ARG_VAR:
          if(!$this->isCorrectVarName($arg)) {
            return 23;
          }
          $argsXml[$argsCounter++] = array(
            'type' => 'var',
            'value' => $this->getVarName($args[0])
          );
          break;
        case Parser::INS_ARG_SYMB:
          if(!$this->isCorrectSymbName($arg)) {
            return 23;
          }
          $argsXml[$argsCounter++] = array(
            'type' => $this->getSymbType($arg),
            'value' => $this->getSymbValue($arg)
          );
          break;
        case Parser::INS_ARG_LABEL:
          if(!$this->isCorrectSymbName($arg)) {
            return 23;
          }
          $argsXml[$argsCounter++] = array(
            'type' => 'label',
            'value' => $arg
          );
          break;
        case Parser::INS_ARG_TYPE:
          if(!$this->isCorrectSymbName($arg)) {
            return 23;
          }
          $argsXml[$argsCounter++] = array(
            'type' => 'type',
            'value' => $arg
          );
          break;
        default:
          // interní chyba při volání funkce
          return 1;

        $argsCounter++;
      }
    }

    $this->instructions[$this->codeLinesCount] = array(
      'opcode' => $name,
      'args' => $argsXml
    );
  }

  /**
   * Funkce zpracuje pomocí funkce getopt argumenty, dále následuje jen nastavování
   * proměnných dle uvedených parametrů a kontrola zakázaných kombinací argumentů.
   *
   * Pozor: U rozšíření stats záleží na pořadí a podle toho je do souboru zapisováno!
   */
  function parseArgs() {
    $longopts  = array(
        "stats:",
        "loc",
        "comments",
        "labels",
        "jumps",
        "help"
    );

    $options = getopt("", $longopts);

    // Parametr --help nelze kombinovat s žádným dalším parametrem, jinak bude skript ukončen s chybou 10
    if(array_key_exists('help', $options)) {
      if(count($this->argvs) != 2) {
        return 10;
      }
      $this->displayHelp();
    }

    // Chybí-li při zadání --loc, --comments, --labels nebo --jumps parametr --stats, jedná se o chybu 10
    if((array_key_exists('comments', $options) || array_key_exists('loc', $options) || array_key_exists('labels', $options) || array_key_exists('jumps', $options)) && !array_key_exists('stats', $options)) {
      return 10;
    }

    if(array_key_exists('stats', $options)) {
      $this->statsFile = $options['stats'];

      foreach($options as $key => $value) {
        if($key == 'loc' || $key == 'comments' || $key == 'labels' || $key == 'jumps') {
          $this->statsOpts[$key] = true;
        }
      }
    }

    return 0;
  }

  /**
   * Funkce zobrazí nápovědu.
   */
  function displayHelp() {
    echo self::HELP_MESSAGE;
    exit(0);
  }

  /**
   * Zapíše na standartní výstup HTML obsahující XML kód v daném jazyce.
   */
  function writeXml() {
    $xml = new XMLWriter();

    $xml->openMemory();
    $xml->setIndent(true);
    $xml->startDocument($this->xmlVersion, $this->xmlEncoding);
    $xml->startElement($this->xmlRootName);
    $xml->writeAttribute('language', $this->language);

    foreach($this->instructions as $order => $instruction) {
      $xml->startElement('instruction');
      $xml->writeAttribute('order', $order);
      $xml->writeAttribute('opcode', $instruction['opcode']);

      if(isset($instruction['args'])) {
        foreach($instruction['args'] as $order => $arg) {
          $xml->startElement('arg' . $order);
          $xml->writeAttribute('type', $arg['type']);
          $xml->writeRaw($arg['value']);
          $xml->endElement();
        }
      }
      $xml->endElement();
    }

    $xml->endElement();
    echo $xml->outputMemory();
  }

}

?>
