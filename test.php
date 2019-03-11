<?php
$test = new Test($argv);
$result = $test->run();
exit($result);
/**
 * Testovací rámec.
 */
class Test {
  private $argvs;
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
      --parse-script=file soubor se skriptem v PHP 5.6 pro analýzu zdrojového kódu v IPPcode18
        (chybí-li tento parametr, tak implicitní hodnotou je parse.php uložený v aktuálním adresáři)
      --int-script=file soubor se skriptem v Python 3.6 pro interpret XML reprezentace kódu
        v IPPcode18 (chybí-li tento parametr, tak implicitní hodnotou je interpret.py uložený v aktuálním adresáři)
      --testlist=file Slouží pro explicitní zadání seznamu adresářů (zadaných relativními či absolutními cestami) a případně i souborů s testy (zadává se soubor s příponou .src) formou externího souboru file místo načtení testů z aktuálního adresáře (nelze kombinovat s parametrem --directory)
      --match=regexp Slouží pro výběr testů jejichž jmémo je bez přípony (ne cesta) odpovídá zadanému regulárnímu výrazu regexp dle PCRE syntaxe.\n";
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
      $infile = substr_replace($file , 'in', strrpos($file , '.') + 1);
      $tmpinputfile = "$infile.tmp";
      $tmpoutputfile = "$outfile.tmp";
      $tmprcfile = "$rcfile.tmp";
      // chyba při otevírání vstupních souborů (např. neexistence, nedostatečné oprávnění).
      if(!is_readable($file)) {
        return 11;
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
      // Parser
      shell_exec("cat $file | php5.6 $this->parseScript > $tmpinputfile ; echo $? > $tmprcfile");
      $this->results[$file]['infilediff'] = shell_exec("diff $infile $tmpinputfile");
      $amongrc = file_get_contents($tmprcfile);
      $amongrc = str_replace(array("\r", "\n"), '', $amongrc);
      if($amongrc == "0") {
        // Interpret
        shell_exec("python3.6 $this->interpretScript --source $tmpinputfile > $tmpoutputfile ; echo $? > $tmprcfile");
        $this->results[$file]['outfilediff'] = shell_exec("diff $outfile $tmpoutputfile");
      } else {
        $this->results[$file]['outfilediff'] = "unknown";
      }
      $this->results[$file]['rcfilediff'] = shell_exec("diff -w $rcfile $tmprcfile");
    }
    return 0;
  }
  /**
   * Funkce zpracuje pomocí funkce getopt argumenty, dále následuje jen nastavování
   * proměnných dle uvedených parametrů a kontrola zakázaných kombinací argumentů.
   */
  function parseArgs() {
    $longopts  = array(
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
    $testPartialResultSuccessTotalCount = 0;
    $testPartialResultTotalCount = $testCount*3;
    $folders = [];
    fwrite(STDOUT, "<html xmlns='http://www.w3.org/1999/xhtml' dir='ltr' lang='cs-cz' xml:lang='cs-cz'>\n");
    foreach($this->results as $srcfile => $info) {
      $testResult = "false";
      $name = explode(".", basename($srcfile))[0];
      $infilleddiff = $info['infilediff'] ? "false" : "true";
      $outputfilediff = $info['outfilediff'] ? "false" : "true";
      $rcfilediff = $info['rcfilediff'] ? "false" : "true";
      $testPartialResult = 0;
      if($infilleddiff == "true") $testPartialResult++;
      if($outputfilediff == "true") $testPartialResult++;
      if($rcfilediff == "true") $testPartialResult++;
      $testPartialResultSuccessTotalCount += $testPartialResult;
      if($infilleddiff == "true" && $outputfilediff == "true" && $rcfilediff == "true") {
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
      fwrite(STDOUT, "\n\n<h1>Jméno testu: $name</h1>\n");
      fwrite(STDOUT, "Složka: $dirname\n");
      fwrite(STDOUT, "Soubor .src: $srcfile\n");
      fwrite(STDOUT, "\nProvedené testy:\n");
      fwrite(STDOUT, "<ul>\n");
      fwrite(STDOUT, "<li>Test porovnání vstupu intepretace: $infilleddiff</li>\n");
      fwrite(STDOUT, "<li>Test porovnání výstupu interpretace: $outputfilediff</li>\n");
      fwrite(STDOUT, "<li>Test návratového kódu: $rcfilediff</li>\n");
      fwrite(STDOUT, "</ul>\n");
      fwrite(STDOUT, "<h1>Úspěšnost testu: $testResult ($testPartialResult/3)</h1>\n");
      fwrite(STDOUT, "#############################################################\n");
    }
    fwrite(STDOUT, "\n\n<h1>Celková úspěšnost: $successTests/$testCount (celková úspěšnost všech podtestů: $testPartialResultSuccessTotalCount/$testPartialResultTotalCount)</h1>\n");
    fwrite(STDOUT, "<h1>Celková úspěšnost dle složek:\n\n");
    foreach($folders as $name => $results) {
      $successTests = $results['successTests'];
      $testCount = $results['testCount'];
      $testPartialResultSuccessTotalCount = $results['testpartialresultsuccesstotalcount'];
      $testPartialResultTotalCount = $results['testpartialresulttotalcount'];
      fwrite(STDOUT, "\n$name : $successTests/$testCount (celková úspěšnost všech podtestů: $testPartialResultSuccessTotalCount/$testPartialResultTotalCount)\n");
    }
    fwrite(STDOUT, "</html>");
  }
}
?>