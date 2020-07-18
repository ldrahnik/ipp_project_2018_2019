<?php

$test = new Test($argv);
$result = $test->run();
exit($result);

/**
 * Testovací rámec.
 */
class Test {

  private $argvs;
  private $parseOnly = false;
  private $intOnly = false;
  private $recursive = false;
  private $directory;
  private $parseScript;
  private $interpretScript;

  // Slouží pro explicitní zadání seznamu adresářů (zadaných relativními či absolutními cestami) a případně i souborů s testy (zadává se soubor s příponou .src)-
  private $testlist = null;

  // Dále podporujte parametr --match=regexp pro výběr testů, jejichž jméno bez přípony (ne cesta) odpovídá zadanému regulárnímu výrazu regexp dle PCRE syntaxe.
  private $match = null;

  // Data výsledků testů a jejich porovnání s originálními souboru pomocí diff zobrazující se v HTML stránce.
  private $results = array();

  const HELP_MESSAGE = "Testovací rámec:
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
(tento parametr se nesmí kombinovat s parametrem --parse-script)\n";

  /**
   * Konstruktor přijímající argumenty uvedené v příkazové řádce.
   */
  function __construct($argvs) {
    $this->argvs = $argvs;
  }

  /**
   * Funkce se volá hned po zavolání konstruktoru.
   * Funkce poté volá funkci na parsování argumentů.
   * Funkce poté pokud je zadaný testlist soubor připravý pro funkci runTests.
   * Funkce zavolá funkci runTests.
   * Funkce zavolá funkci writeHtml a končí.
   */
  function run() {
    $result = $this->parseArgs();
    if($result != 0) {
      return $result;
    }
    if($this->testlist) {
      if($file = fopen($this->testlist, "r")) {
        while(($line = fgets($file)) !== false) {
          $line = preg_replace("/[\n\r]/","", $line);
          if(is_dir($line)) {
            $result = $this->runTests($line);
          } else {
            $result = $this->runTests(null, $line);
          }
          if($result != 0) {
            return $result;
          }
        }
      }
    } else {
      $result = $this->runTests($this->directory);
      if($result != 0) {
        return $result;
      }
    }
    $result = $this->writeHtml();
    if($result != 0) {
      return $result;
    }
    return 0;
  }

  /**
   * Funkce slouží jako wrapper pro funkci glob ke které přidává možnost použít rekurzivní procházení složek či nikoliv.
   */
  function glob($base, $pattern, $flags = 0, $recursive = false) {
	  if(substr($base, -1) !== DIRECTORY_SEPARATOR) {
		  $base .= DIRECTORY_SEPARATOR;
	  }
	  $files = glob($base . $pattern, $flags);
    if($recursive) {
	      foreach (glob($base . '*', GLOB_ONLYDIR|GLOB_NOSORT|GLOB_MARK) as $dir) {
		    $dirFiles = $this->glob($dir, $pattern, $flags, true);
		    if($dirFiles !== false) {
			    $files = array_merge($files, $dirFiles);
		    }
	    }
    }
	  return $files;
  }

 /**
  * Funkce spustí testy, pokud existuje zadaný soubor --testlist=file tak prioritizuje soubor daný rozšířením, pokud ne,
  * prohledává uvedenou složku kde hledá všechny .src soubory a ke konkrétnímu testu dohledává vždy spjaté soubory(.rc, .out, .in).
  *
  * Funkce dále kontroluje, zda se všechny soubory dají otevřít (existují, mají oprávnění nebo má program oprávnění pro případné vytvoření prázdných souborů)
  *
  * Poté funkce spustí parser.php a intepret.py. Chybová návratová hodnota je první, která se vyskytne. Pokud selže parser.php, chybová hodnota se bude kontrolovat z něj.
  */
  function runTests($directory = null, $file = null) {
    if($file) {
      $files = [$file];
    } else {
      $files = $this->glob($directory, '*.src', 0, $this->recursive);
    }
    foreach($files as $file) {
      if($this->match) {
        $filename = basename($file);
        $basename = substr($filename, 0, strrpos($filename, "."));
        if(!preg_match($this->match, $basename)) {
          continue;
        }
      }
      $rcfile = substr_replace($file , 'rc', strrpos($file , '.') + 1);
      $outfile = substr_replace($file , 'out', strrpos($file , '.') + 1);
      $outfileXml = substr_replace($file , 'xml', strrpos($file , '.') + 1);
      $infile = substr_replace($file , 'in', strrpos($file , '.') + 1);
      $tmpinputfile = "$infile.tmp";
      $tmpoutputfile = "$outfile.tmp";
      $tmprcfile = "$rcfile.tmp";
      $tmpinputfileWithFile = "$tmpinputfile.ttmp";
      $tmpdiffrcfile = "$tmpinputfile.rc.ttmp";
      $tmpjexamxmljar = "$tmpinputfile.jexamxml.tmp";

      // chyba při otevírání vstupních souborů (např. neexistence, nedostatečné oprávnění).
      if(!is_readable($file)) {
        return 11;
      }
      // Pokud soubor s příponou .xml chybí (both testy)
      if(!$this->parseOnly && !$this->intOnly) {
        if (!is_readable($outfileXml)) {
          // chyba při otevření výstupních souborů pro zápis (např. nedostatečné oprávnění).
          if (!touch($outfileXml)) {
            return 12;
          }
        }
      }
      // Pokud soubor s příponou in nebo out chybí, tak se automaticky dogeneruje prázdný soubor. V případě chybějícího souboru s příponou rc se vygeneruje soubor obsahující návratovou hodnotu 0.
      if(!is_readable($outfile)) {
        // chyba při otevření výstupních souborů pro zápis (např. nedostatečné oprávnění).
        if(!touch($outfile)) {
          return 12;
        }
      }
      if(!is_readable($infile)) {
        // chyba při otevření výstupních souborů pro zápis (např. nedostatečné oprávnění).
        if(!touch($infile)) {
          return 12;
        }
      }
      if(!is_readable($rcfile)) {
        // chyba při otevření výstupních souborů pro zápis (např. nedostatečné oprávnění).
        if(!file_put_contents($rcfile, "0")) {
          return 12;
        }
      }
      if(!is_readable($tmprcfile)) {
        if(!touch($tmprcfile)) {
          return 12;
        }
      }
      if(!is_readable($tmpinputfile)) {
        if(!touch($tmpinputfile)) {
          return 12;
        }
      }
      if(!is_readable($tmpinputfileWithFile)) {
        if(!touch($tmpinputfileWithFile)) {
          return 12;
        }
      }
      if(!is_readable($tmpdiffrcfile)) {
        if(!touch($tmpdiffrcfile)) {
          return 12;
        }
      }
      if(!is_readable($tmpjexamxmljar)) {
        if(!touch($tmpjexamxmljar)) {
          return 12;
        }
      }

      // Parser
      $amongrc = "0";
      if(!$this->intOnly) {
        shell_exec("cat $file | php7.3 $this->parseScript > $tmpinputfileWithFile ; echo $? > $tmprcfile");
        shell_exec("grep -F -x -v -f $file -w $tmpinputfileWithFile > $tmpinputfile");
        shell_exec("sed -i 's/^.*<?xml/<?xml/' $tmpinputfile");

        // dále pokračuje interpret, tzn. výstupní soubor z parseru bude mít v referenčním řešení koncovku .xml
        if(!$this->parseOnly) {
          shell_exec("java -jar $( dirname $this->parseScript)/jexamxml.jar $outfileXml $tmpinputfile $tmpjexamxmljar $( dirname $this->parseScript)/options ; echo $? > $tmpdiffrcfile");
        } else {
          shell_exec("java -jar $( dirname $this->parseScript)/jexamxml.jar $outfile $tmpinputfile $tmpjexamxmljar $( dirname $this->parseScript)/options ; echo $? > $tmpdiffrcfile");
        }
        $this->results[$file]['infilediff'] = file_get_contents($tmpdiffrcfile);
        $amongrc = file_get_contents($tmprcfile);
        $amongrc = str_replace(array("\r", "\n"), '', $amongrc);
      }

      // Interpret
      if(!$this->parseOnly) {
        if($amongrc == "0") {

          // --int-only potřebuje přímo .src soubor (parser se na zpracování .in souboru na .src nepoužije)
          if($this->intOnly) {
             shell_exec("python3.6 $this->interpretScript --source $file --input $infile > $tmpoutputfile ; echo $? > $tmprcfile");
          } else {
             shell_exec("python3.6 $this->interpretScript --source $tmpinputfile --input $infile > $tmpoutputfile ; echo $? > $tmprcfile");
          }
          shell_exec("diff -w $outfile $tmpoutputfile ; echo $? > $tmpdiffrcfile");
          $this->results[$file]['outfilediff'] = file_get_contents($tmpdiffrcfile);
        }
      }

      $amongrc = file_get_contents($tmprcfile);
      $amongrc = str_replace(array("\r", "\n"), '', $amongrc);
      $rc = file_get_contents($rcfile);
      $rc = str_replace(array("\r", "\n"), '', $rc);
      $this->results[$file]['rcfilediff'] = $rc == $amongrc ? "true" : "false";

      // Je nutné smazat dočasné soubory (sloužily pouze k porovnání)
      if(file_exists($tmprcfile))
        unlink($tmprcfile);

      if(file_exists($tmpinputfileWithFile))
        unlink($tmpinputfileWithFile);

      if(file_exists($tmpdiffrcfile))
        unlink($tmpdiffrcfile);

      if(file_exists($tmpoutputfile))
        unlink($tmpoutputfile);

      if(file_exists($tmpinputfile))
        unlink($tmpinputfile);

      if(file_exists($tmpjexamxmljar))
        unlink($tmpjexamxmljar);
    }
    return 0;
  }

  /**
   * Funkce zpracuje pomocí funkce getopt argumenty, dále následuje jen nastavování
   * proměnných dle uvedených parametrů a kontrola zakázaných kombinací argumentů.
   */
  function parseArgs() {
    $longopts  = array(
        "parse-only",
        "int-only",
        "recursive",
        "directory:",
        "parse-script:",
        "help",
        "int-script:",
        'testlist:',
        'match:',
        'stats:'
    );
    $options = getopt("", $longopts);
    // Parametr --help nelze kombinovat s žádným dalším parametrem, jinak bude skript ukončen s chybou 10
    if(array_key_exists('help', $options)) {
      if(count($this->argvs) != 2) {
        return 10;
      }
      $this->displayHelp();
    }
    // parameter int-only se nesmí kombinovat s parametrem --parse-script
    if(array_key_exists('int-only', $options) && array_key_exists('parse-only', $options)) {
       return 10;
    }
    if(array_key_exists('parse-only', $options)) {
      $this->parseOnly = true;
    }
    if(array_key_exists('int-only', $options)) {
      $this->intOnly = true;
    }
    if(array_key_exists('recursive', $options)) {
      $this->recursive = true;
    }
    if(array_key_exists('directory', $options)) {
      $this->directory = $options['directory'];
    } else {
      $this->directory = getcwd();
    }
    if(array_key_exists('parse-script', $options)) {
      $this->parseScript = $options['parse-script'];
    } else {
      $this->parseScript = __DIR__ . DIRECTORY_SEPARATOR . 'parse.php';
    }
    if(array_key_exists('int-script', $options)) {
      $this->interpretScript = $options['int-script'];
    } else {
      $this->interpretScript = __DIR__ . DIRECTORY_SEPARATOR . 'interpret.py';
    }
    if(array_key_exists('testlist', $options)) {
      $this->testlist = $options['testlist'];
      // nelze kombinovat s parametrem --directory
      if(array_key_exists('directory', $options)) {
        return 10;
      }
    }
    if(array_key_exists('match', $options)) {
      $this->match = $options['match'];
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
  * Zapíše na standartní výstup HTML obsahující výsledky provedených testů. U každého testu obsahují výsledky porovnání:
  * 1. Test porovnání vstupu intepretace (true, false)
  * 2. Test porovnání výstupu interpretace (true, false)
  * 3. Test návratového kódu (true, false)
  *
  * HTML obsahuje nastavený jazyk cs-cz z důvodu diakritiky a textu česky.
  */
  function writeHtml() {
    $testCount = count($this->results);
    $successTests = 0;
    $testPartialResultTotalCount = $testCount*3;
    $folders = [];
    fwrite(STDOUT, "<!DOCTYPE html>");
    fwrite(STDOUT, "<html xmlns='http://www.w3.org/1999/xhtml' dir='ltr' lang='cs-cz' xml:lang='cs-cz'>\n");
    fwrite(STDOUT, "<head><meta charset=\"UTF-8\"></head>");
    fwrite(STDOUT, "<body>");

    // Testy očíslujeme od 1
    fwrite(STDOUT, "<h1>Testy:</h1>\n\n");
    fwrite(STDOUT, "\n#############################################################\n");

    $testIterator = 1;
    foreach($this->results as $srcfile => $info) {
      $testResult = "false";
      $name = explode(".", basename($srcfile))[0];

      $testPartialResult = 0;
      $testPartialCount = 0;

      if(!$this->intOnly) {
        $infilleddiff = $info['infilediff'] == 0 ? "true" : "false";
        $testPartialCount++;
        if($infilleddiff == "true") $testPartialResult++;
      }

      $rcfilediff = $info['rcfilediff'];
      $testPartialCount++;

      if(!$this->parseOnly && array_key_exists('outfilediff', $info) && $rcfilediff != "true") {
        $outputfilediff = $info['outfilediff'] == 0 ? "true" : "false";
        $testPartialCount++;
        if($outputfilediff == "true") $testPartialResult++;
      }

      if($rcfilediff == "true") $testPartialResult++;
      if(((isset($infilleddiff) && $infilleddiff == "true") || !isset($infilleddiff)) &&
         ((isset($outputfilediff) && $outputfilediff == "true") || !isset($outputfilediff)) &&
         ((isset($rcfilediff) && $rcfilediff == "true") || !isset($rcfilediff))) {
        $successTests++;
        $testResult = "true";
      }
      $dirname = dirname($srcfile);
      if(!array_key_exists($dirname, $folders)) {
        $folders[$dirname]['testCount'] = 0;
        $folders[$dirname]['successTests'] = 0;
        $folders[$dirname]['testpartialresultsuccesstotalcount'] = 0;
        $folders[$dirname]['testpartialresulttotalcount'] = 0;
      }
      if($testResult == "true")
        $folders[$dirname]['successTests'] += 1;
      $folders[$dirname]['testCount'] += 1;
      $folders[$dirname]['testpartialresultsuccesstotalcount'] += $testPartialResult;
      $folders[$dirname]['testpartialresulttotalcount'] += 3;
      $resultHeadingStyleColor = $testResult == "true" ? 'color: green;' : 'color: red;';
      $resultHeadingStyle = "style=\"$resultHeadingStyleColor\"";

      fwrite(STDOUT, "\n\n<h1 $resultHeadingStyle>$testIterator. $name ($testPartialResult/$testPartialCount)</h1>\n");
      fwrite(STDOUT, "<p>Složka: $dirname</p>\n");
      fwrite(STDOUT, "\n\nProvedené testy:\n");
      fwrite(STDOUT, "<ul>\n");

      // Pouze parser
      if(!$this->intOnly) {
        $interpretInputHeadingStyleColor = $infilleddiff == "true" ? 'color: green;' : 'color: red;';
        $interpretInputHeadingStyle = "style=\"$interpretInputHeadingStyleColor\"";
        fwrite(STDOUT, "<li>Test porovnání výstupu parseru: <span $interpretInputHeadingStyle>$infilleddiff</li>\n");
      }

      // Pouze interpret
      if(!$this->parseOnly && array_key_exists('outfilediff', $info) && $rcfilediff != "true") {
        $interpretOutputHeadingStyleColor = $outputfilediff == "true" ? 'color: green;' : 'color: red;';
        $interpretOutputHeadingStyle = "style=\"$interpretOutputHeadingStyleColor\"";
        fwrite(STDOUT, "<li>Test porovnání výstupu interpretace: <span $interpretOutputHeadingStyle>$outputfilediff</li>\n");
      }

      $returnCodeHeadingColor = $rcfilediff == "true" ? 'color: green;' : 'color: red;';
      $returnCodeHeadingStyleColor = "style=\"$returnCodeHeadingColor\"";
      fwrite(STDOUT, "<li>Test návratového kódu: <span $returnCodeHeadingStyleColor>$rcfilediff</span></li>\n");
      fwrite(STDOUT, "</ul>\n");
      $testIterator++;
    }
    fwrite(STDOUT, "\n#############################################################\n");
    $testsResultHeadingColor = $successTests == $testCount ? 'color: green;' : 'color: red;';
    $testsResultHeadingStyleColor = "style=\"$testsResultHeadingColor\"";
    fwrite(STDOUT, "\n\n<h1 $testsResultHeadingStyleColor>Celková úspěšnost: $successTests/$testCount</h1>\n");

    fwrite(STDOUT, "<br>");
    fwrite(STDOUT, "<br>");
    fwrite(STDOUT, "<br>");

    fwrite(STDOUT, "<h1>Složky:</h1>\n\n");
    fwrite(STDOUT, "\n#############################################################\n");

    // Složky očíslujeme od 1
    $folderIterator = 1;
    $successFolders = 0;
    foreach($folders as $name => $results) {
      $successTests = $results['successTests'];
      $testCount = $results['testCount'];
      $testPartialResultSuccessTotalCount = $results['testpartialresultsuccesstotalcount'];
      $testPartialResultTotalCount = $results['testpartialresulttotalcount'];

      $folderHeadingColor = $successTests == $testCount ? 'color: green;' : 'color: red;';
      $folderHeadingStyleColor = "style=\"$folderHeadingColor\"";
      fwrite(STDOUT, "<h1 $folderHeadingStyleColor><p>\n$folderIterator. $name ($successTests/$testCount) </p></h1>\n");

      if($successTests == $testCount) {
         $successFolders += 1;
      }
      $folderIterator++;
    }
    fwrite(STDOUT, "\n#############################################################\n");
    $foldersCount = count($folders);
    $foldersResultHeadingColor = $successFolders == $foldersCount ? 'color: green;' : 'color: red;';
    $foldersResultHeadingStyleColor = "style=\"$foldersResultHeadingColor\"";
    fwrite(STDOUT, "\n\n<h1 $foldersResultHeadingStyleColor>Celková úspěšnost složek: $successFolders/$foldersCount</h1>\n");

    fwrite(STDOUT, "</body>");
    fwrite(STDOUT, "</html>");
  }
}

?>
