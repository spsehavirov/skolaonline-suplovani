# Použití a konfigurace

[Zpět na hlavní stránku](../README.md)

Příkazy spouštějte z kořene projektu. Před prvním použitím dokončete
[instalaci](installation.md).

## Stahování bez prohlížeče

`so_soap.py` je přímý HTTP stahovač žákovského suplování. Přihlásí se do webové
aplikace a odešle její exportní formulář; nepotřebuje Selenium ani otevřený prohlížeč.

```bash
./so_soap.py --date "15.10.2026"
```

Přijímá datum jako `15.10.2026`, `15.10.26` nebo `2026-10-15`.
Bez `--date` použije `DATE_TO_PROCESS`, pokud je nastavené v prostředí nebo `.env`,
jinak aktuální den. Příkaz hodnotu v `.env` nepřepisuje.

XML uloží do sledované složky pod názvem `so_suplovani_students-2026-10-15.xml`
a připojí soubor s filtry konkrétního běhu.
[Volby filtrů](filtering.md) jsou společné pro oba stahovače.

## Stahování přes Selenium

Alternativní stahovač ovládá prohlížeč pomocí SeleniumBase. Dosavadní použití bylo
s Chrome na macOS; přímý HTTP stahovač tuto závislost nemá.

```bash
./so_download.py --date "15.10.2026" --headless
```

Používá stejné přihlašovací údaje, filtry i cílový název XML jako `so_soap.py`.
Volby jako `--headless` předává SeleniumBase.

## Monitor a ručně dodané XML

Monitor spusťte v samostatném terminálu:

```bash
./suplovani.py
```

Při startu zpracuje již přítomná XML a potom sleduje nové nebo změněné soubory.
Podle obsahu rozpozná žákovský či učitelský výpis. Ručně exportované XML můžete
vložit přímo do `watch/`; bez doprovodného souboru použije pravidla uložená v configu.

Po úspěšném zpracování archivuje XML i jeho případný soubor `.filters.json`
do `watch/processed/`. Opakovaný archiv stejného názvu dostane vlastní podsložku.
Existující čekající XML se při dalším stahování nepřepíše; nechte ho nejprve zpracovat.

## Nastavení výstupů

Základní provozní nastavení je v `config.yaml`:

```yaml
settings:
  watch_folder: ./watch
  output_folder: ./outputs
  check_interval: 2
  output:
    - csv
    - html
    - pdf
    - png
  include: []
  exclude: []
```

| Nastavení | Význam |
| --- | --- |
| `watch_folder` | Složka se vstupními XML. |
| `output_folder` | Složka s hotovými výpisy. |
| `check_interval` | Interval kontroly vstupů v sekundách. |
| `output` | Seznam požadovaných výstupních formátů. |
| `include`, `exclude` | Uložená pravidla tříd; [podrobnosti](filtering.md). |

PDF potřebuje předem vytvořené HTML a PNG potřebuje PDF, proto zachovejte pořadí
`html`, `pdf`, `png`. Při změně `watch_folder` nebo `check_interval` restartujte
monitor; ostatní nastavení načítá pro každý nový výpis.

| Výpis | Formáty | Názvy výstupů |
| --- | --- | --- |
| Žáci | CSV, HTML, PDF, PNG | `supl_26-10-15_ct.*`; PNG po stránkách jako `supl_26-10-15_ct_1.png`. |
| Učitelé | CSV, HTML, PDF | `suplovani_2026_10_15.*` a `absences_2026_10_15.csv`. |

Pro zpracování pouze učitelských XML vynechte `png` ze seznamu formátů.
Žákovská tabulka má symetrické okraje; historické levé odsazení pro FEH je odstraněné.
PNG se generuje z PDF v rozlišení 600 DPI.

Opakované zpracování stejného žákovského výpisu obnoví jeho soubory pro daný den
a formát. Ovlivnit podobu výpisu lze úpravou `templates/students.html` nebo
`templates/teachers.html`; změna žákovské šablony se projeví i v PDF a PNG.

## Nápověda

```bash
./so_soap.py --help
./so_download.py --help
./suplovani.py --help
```

Pravidla pro předávání filtrů a řešení vadného doprovodného souboru jsou v
[návodu k filtrování](filtering.md#platnost-pravidel-a-předání-monitoru).
