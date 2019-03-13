<?php

$parser = new Parser($argv);
$result = $parser->run();
exit($result);

/**
 * Analyzátor kódu v IPPcode18.
 */
class Parser {

  private $xmlVersion = '1.0';
  private $xmlEncoding = 'UTF-8';
  private $xmlRootName = 'program';

  private $language = 'IPPcode19';

  private $statsFile = null;
  private $statsOpts = array();

  private $argvs = array();

  // vypíše do statistik počet řádků, na kterých se vyskytoval komentář
  private $commentsCount = 0;

  // nepočítají se prázdné řádky, ani řádky obsahující pouze komentář, ani úvodní řádek
  private $codeLinesCount = 0;

  private $instructios = array();

  const HELP_MESSAGE = "Analyzátor kódu v IPPcode19:
      --help vypíše na standardní výstup nápovědu skriptu (nenačítá žádný vstup)
      --stats=file slouží pro zadání souboru file, kam se agregované statistiky
      budou vypisovat (po řádcích dle pořadí v dalších parametrech)
      --loc vypíše do statistik počet řádků s instrukcemi (nepočítají se prázdné
       řádky, ani řádky obsahující pouze komentář, ani úvodní řádek)
      --comments vypíše do statistik počet řádků, na kterých se vyskytoval
      komentář\n";

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
    if(!preg_match('/^(LF|TF|GF){1}@[a-zA-Z_\-$&%*]{1}[a-zA-Z0-9_\-$&%*]*$/', $name)) {
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

    /*
     * U literálů typu string při zápisu do XML nepřevádějte původní escape sekvence, ale
     * pouze pro problematické znaky v XML (např. <, >, &) využijte odpovídající XML entity (např.
     * &lt;, &gt;, &amp;).
     */
    if($string) {
      $search = array('&lt;', '&gt;', '&amp;');
      $replace = array('<', '>', '&');

      $name = str_replace($search, $replace, $name);
    }

    if($string || $int || $bool) {
      return true;
    }

    return false;
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
    return ($name == 'bool' || $name == 'string' | $name == 'int');
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
    return $this->getSymbType($name) == 'var' ? $name : explode("@", $name)[1];
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

      // pokud na řádku něco je, musí to být nějaká z instrukcí nebo komentář
      if($exploded[0]) {
        $this->codeLinesCount++;

        switch(strtoupper($exploded[0])) {
          case "MOVE":
          case "INT2TOCHAR":
          case "NOT":
            if(count($exploded) != 3) {
              return 23;
            }
            if(!$this->isCorrectVarName($exploded[1])) {
              return 23;
            }
            if(!$this->isCorrectSymbName($exploded[2])) {
              return 23;
            }
            $this->instructions[$this->codeLinesCount] = array(
              'opcode' => $exploded[0],
              'args' => array(
                '1' => array(
                  'type' => 'var',
                  'value' => $exploded[1]
                ),
                '2' => array(
                  'type' => $this->getSymbType($exploded[2]),
                  'value' => $this->getSymbValue($exploded[2])
                )
              )
            );
            break;
          case "CREATEFRAME":
          case "PUSHFRAME":
          case "POPFRAME":
          case "RETURN":
          case "BREAK":
            if(count($exploded) != 1) {
              return 23;
            }
            $this->instructions[$this->codeLinesCount] = array(
              'opcode' => $exploded[0]
            );
            break;
          case "POPS":
          case "DEFVAR":
            if(count($exploded) != 2) {
              return 23;
            }
            if(!$this->isCorrectVarName($exploded[1])) {
              return 23;
            }
            $this->instructions[$this->codeLinesCount] = array(
              'opcode' => $exploded[0],
              'args' => array(
                '1' => array(
                  'type' => 'var',
                  'value' => $exploded[1]
                )
              )
            );
            break;
          case "CALL":
            if(count($exploded) != 2) {
              return 23;
            }
            if(!$this->isCorrectLabelName($exploded[1])) {
              return 23;
            }
            $this->instructions[$this->codeLinesCount] = array(
              'opcode' => $exploded[0],
              'args' => array(
                '1' => array(
                  'type' => 'label',
                  'value' => $exploded[1]
                )
              )
            );
            break;
          case "PUSHS":
          case "WRITE":
          case "DPRINT":
            if(count($exploded) != 2) {
              return 23;
            }
            if(!$this->isCorrectSymbName($exploded[1])) {
              return 23;
            }
            $this->instructions[$this->codeLinesCount] = array(
              'opcode' => $exploded[0],
              'args' => array(
                '1' => array(
                  'type' => $this->getSymbType($exploded[1]),
                  'value' => $this->getSymbValue($exploded[1])
                )
              )
            );
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
            if(count($exploded) != 4) {
              return 23;
            }
            if(!$this->isCorrectVarName($exploded[1])) {
              return 23;
            }
            if(!$this->isCorrectSymbName($exploded[2])) {
              return 23;
            }
            if(!$this->isCorrectSymbName($exploded[3])) {
              return 23;
            }
            $this->instructions[$this->codeLinesCount] = array(
              'opcode' => $exploded[0],
              'args' => array(
                '1' => array(
                  'type' => 'var',
                  'value' => $exploded[1]
                ),
                '2' => array(
                  'type' => $this->getSymbType($exploded[2]),
                  'value' => $this->getSymbValue($exploded[2])
                ),
                '3' => array(
                  'type' => $this->getSymbType($exploded[3]),
                  'value' => $this->getSymbValue($exploded[3])
                )
              )
            );
            break;
          case "READ":
            if(count($exploded) != 3) {
              return 23;
            }
            if(!$this->isCorrectVarName($exploded[1])) {
              return 23;
            }
            if(!$this->isCorrectTypeName($exploded[2])) {
              return 23;
            }
            $this->instructions[$this->codeLinesCount] = array(
              'opcode' => $exploded[0],
              'args' => array(
                '1' => array(
                  'type' => 'var',
                  'value' => $exploded[1]
                ),
                '2' => array(
                  'type' => 'type',
                  'value' => $exploded[2]
                )
              )
            );
            break;
          case "STRLEN":
          case "TYPE":
            if(count($exploded) != 3) {
              return 23;
            }
            if(!$this->isCorrectVarName($exploded[1])) {
              return 23;
            }
            if(!$this->isCorrectSymbName($exploded[2])) {
              return 23;
            }
            $this->instructions[$this->codeLinesCount] = array(
              'opcode' => $exploded[0],
              'args' => array(
                '1' => array(
                  'type' => 'var',
                  'value' => $exploded[1]
                ),
                '2' => array(
                  'type' => $this->getSymbType($exploded[2]),
                  'value' => $this->getSymbValue($exploded[2])
                )
              )
            );
            break;
          case "LABEL":
          case "JUMP":
            if(count($exploded) != 2) {
              return 23;
            }
            if(!$this->isCorrectLabelName($exploded[1])) {
              return 23;
            }
            $this->instructions[$this->codeLinesCount] = array(
              'opcode' => $exploded[0],
              'args' => array(
                '1' => array(
                  'type' => 'label',
                  'value' => $exploded[1]
                )
              )
            );
            break;
          case "JUMPIFEQ":
          case "JUMPIFNEQ":
            if(count($exploded) != 4) {
              return 23;
            }
            if(!$this->isCorrectLabelName($exploded[1])) {
              return 23;
            }
            if(!$this->isCorrectSymbName($exploded[2])) {
              return 23;
            }
            if(!$this->isCorrectSymbName($exploded[3])) {
              return 23;
            }
            $this->instructions[$this->codeLinesCount] = array(
              'opcode' => $exploded[0],
              'args' => array(
                '1' => array(
                  'type' => 'label',
                  'value' => $exploded[1]
                ),
                '2' => array(
                  'type' => $this->getSymbType($exploded[2]),
                  'value' => $this->getSymbValue($exploded[2])
                ),
                '3' => array(
                  'type' => $this->getSymbType($exploded[3]),
                  'value' => $this->getSymbValue($exploded[3])
                )
              )
            );
            break;
          default:
            // neznámý nebo chybný operační kód ve zdrojovém kódu zapsaném v IPPcode19
            return 22;
        }
      }
    }

    return 0;
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

    // Chybí-li při zadání --loc nebo --comments parametr --stats, jedná se o chybu 10
    if((array_key_exists('comments', $options) || array_key_exists('loc', $options)) && !array_key_exists('stats', $options)) {
      return 10;
    }

    if(array_key_exists('stats', $options)) {
      $this->statsFile = $options['stats'];

      foreach($options as $key => $value) {
        if($key == 'loc' || $key == 'comments') {
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
          $xml->text($arg['value']);
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
