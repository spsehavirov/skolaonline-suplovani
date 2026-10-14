![Python](https://img.shields.io/badge/python-3.13-blue?style=for-the-badge&logo=python)
![Status](https://img.shields.io/badge/status-active-brightgreen?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/spsehavirov/skolaonline-suplovani?style=for-the-badge)
![License](https://img.shields.io/github/license/spsehavirov/skolaonline-suplovani?style=for-the-badge)

# 📢 Suplování ve ŠkolaOnline

Tato sada skriptů vznikla z potřeby přizpůsobit export dat z ŠkolaOnline pro suplování a následné zobrazení na TV ve vestibulu školy. 

## 📌 **Proč?** 
ŠO bohužel nenabízí API, takže data je nutné stáhnout ručně ve formátu XML a následně je zpracovat.

## 🔧 **Co skript(y) umí?**  
- ✅ Překonvertovat soubory, při startu programu
- ✅ Automaticky sledovat složku pro nové soubory
- ✅ Stahovat rozvrh suplování přímo ze ŠO 
- ✅ Zpracovávat XML do CSV, HTML a PDF a png (číslované po stránkách)
- ✅ Barvení záhlaví dle dne v týdnu
- ✅ Filtrovat zobrazení pro vynechání tříd nebo naopak zahrnutí jen jich do výpisu
- ✅ Filtrovat výpis jen do určité hodiny (konec dne)

- 🚧 Volba šablony, pro stažení (aktuálně je natvrdo naše školní)
- 🚧 Najít jak obejít ŠO formulář a poslat data napřímo tak, abychom hned dostali výsledek (HTTPS POST místo Selenium)

---

## ⚡ **Jak to funguje?**
### 📂 **Struktura projektu**
#### 🖥️ `suplovani.py`  
👀 Sleduje složku (výchozí: `./watch`) a při detekci **platného XML** (pro žáky nebo učitele) ho automaticky převede do CSV, HTML a PDF.

#### 🌐 `so_download.py`  
🤖 Automatizuje **stahování dat ze ŠkolaOnline** pomocí prohlížeče (headless mode). Stačí zadat požadované datum a skript provede přihlášení + stažení dat.

#### 🌐 `so_soap.py`
🧪 Nová varianta stahování **bez prohlížeče** – využívá přímo HTTP/form POST (stejný požadavek, který posílá web). Je rychlejší a neotevírá žádný browser.

#### 🧭 `so_recorder.py`
🧾 Záznamník manuálních kliků – otevře přihlášený prohlížeč a uloží všechny HTTP požadavky do JSON (pro pozdější reverse-engineering a psaní skriptů).

⚠️ **.env** soubor
Aby bylo možné příhlásit se do `skolaonline.cz` z automatizovaného prohlížeče, je nutné mít ve složce vytvořený soubor `.env` (viz instalace)

🖥️ **Prohlížeč**
Testováno s prohlížečem Chrome (na macOS), ale Selenium by mělo pracovat i s Firefoxem a Edgem.

---

## 🚀 **Instalace & Použití**
### 1️⃣ **Nastavení přihlašovacích údajů**
Nejprve vytvořte soubor `.env` s přihlašovacími údaji:

```ini
SO_USER=<vas-ucet-ve-skoleonline>
SO_PASS=<vase-heslo-pro-skoluonline>
```
### 2️⃣ Instalace závislostí
Vyžaduje Python **3.13** (na macOS: `brew install python@3.13`). Instalátor vytvoří
prostředí `.venv` pomocí `python3.13`, nezávisle na výchozí verzi Pythonu.
Instalace a exporty jsou ověřovány na Pythonu 3.13.

```bash
$ ./install
$ source .venv/bin/activate
```
Stahovače a monitor při přímém spuštění (`./so_soap.py`, `./so_download.py`,
`./suplovani.py`) automaticky použijí projektové `.venv`, pokud existuje.
Aktivace je stále vhodná pro další příkazy `python` v terminálu.
Bez `.venv` zůstane použitý současný interpreter, například při starší instalaci na Raspberry Pi.

(`install` nainstaluje i `requests-toolbelt`, kterou používá `so_soap.py` pro multipart/form-data volání.)

Kontrola kompatibility závislostí a exportů (syntetická data, bez přihlášení do ŠO):
```bash
$ python -m pip check
$ python -m unittest discover -s tests -v
```
Pro kontrolu známých zranitelností lze použít [pip-audit](https://github.com/pypa/pip-audit)
z odděleného nástrojového prostředí proti balíčkům v `.venv/lib/python3.13/site-packages`.
Podrobnosti aktualizace: [docs/dependency-security.md](docs/dependency-security.md).

### 3️⃣ Spuštění skriptů
📡 Sledování složky a zpracování XML:
```bash
$ (virt-env) ./suplovani.py # Zapne monitorování složky
```
🌍 Stažení suplování pro konkrétní datum:
```bash
$ (virt-env) ./so_download.py --date "25.2.2025" --headless --clear --exclude=3A,1C # Stáhne data k požadovaného datu
```

🌍 Rychlejší stažení suplování bez prohlížeče:
```bash
$ (virt-env) ./so_soap.py --date "25.2.2025" --clear --exclude=3A,1C --day-end-hour 4
```
Oba stahovače sdílí stejné filtrační volby a názvy XML. `--day-end-hour=4`
omezí výpis žáků i učitelů do 4. hodiny včetně.

### Filtrování hodin a tříd

Nové `--hours` a `--skip` ovlivňují **jen výpis žáků**, všechny způsoby řešení
(včetně „odpadá“, suplování a změn učebny). Přehled absencí a výpis učitelů zachovají.

| Parametr | Význam |
| --- | --- |
| `--hours=3-6` | Zobrazit pouze 3. až 6. hodinu. |
| `--skip=2-4` | Vynechat 2. až 4. hodinu všem třídám. |
| `--skip=1A:2-4` | Vynechat tyto hodiny třídě 1A. |
| `--skip=1A,1B,1C:2-4` | Vynechat je vyjmenovaným třídám. |
| `--skip=1-3:2-4` | Vynechat je všem třídám ročníků 1–3, včetně případných dalších oddělení. |
| `--skip=1A:2-4,1B:1-2,1C:4` | Kombinovat pravidla tříd. |
| `--no-config` | Použít jen filtry příkazu; zachovat nastavení složek, formátů a přihlášení. |
| `--clear` | Ignorovat uložené include/exclude; ostatní uložené filtry zachovat. |

`--skip` lze opakovat. Názvy tříd jsou nezávislé na velikosti písmen.
Jednotlivé hodiny i rozsahy musí být kladné, rozsahy zahrnují oba kraje.
Číselný výběr ročníku je jeden ročník nebo jeden rozsah; seznam před dvojtečkou
je seznam názvů tříd. Pro více výběrů ročníků použijte opakované `--skip`.

```bash
# Divadlo ve 2.–4. hodině pro ročníky 1–3; 3A je úplně vyloučená.
./so_soap.py --date=20.10.2026 --exclude=3A --skip=1-3:2-4

# Výpis hodin 3–6, pro 1A navíc vynechat 4. hodinu.
./so_soap.py --date=20.10.2026 --hours=3-6 --skip=1A:4

# Více různých pravidel v jednom běhu.
./so_download.py --date=20.10.2026 --headless \
  --skip=1A:2-4 --skip=1B:1-2 --skip=1C:4

# Žádné uložené filtry, pouze rozmezí z tohoto příkazu.
./so_soap.py --date=20.10.2026 --no-config --hours=3-6
```

**Uložená pravidla jsou základ.** Seznamy include/exclude z příkazu se přidají
k uloženým seznamům, ale `exclude` vždy vyhrává i při současném `include`.
Rozmezí hodin se skládají průnikem, vynechávané hodiny sjednocením.
Uložený konec dne a `--day-end-hour` jsou další horní mezí; použije se nižší limit.
Prázdný průnik znamená prázdný žákovský výpis.
Vícehodinový záznam `1-6` po vynechání `2-4` vytvoří záznamy `1` a `5-6`.
Filtr se použije před slučováním záznamů, shodně pro CSV, HTML, PDF a PNG.
Neznámé označení hodiny se zachová s upozorněním.

**Změna oproti původnímu chování:** parametry příkazu, včetně `--include`,
`--exclude`, `--clear` a `--day-end-hour`, nyní **nemění `config.yaml` ani `.env`**.
Platí pouze pro konkrétní stažené XML. Trvalé filtry upravujte v `config.yaml`.
Výjimky hodin ukládejte podle data, které se porovnává s datem uvnitř XML:

```yaml
settings:
  exclude: [3A]
  day_end_hour: 7
  student_filters_by_date:
    "2026-10-20":
      hours: "3-6"
      skip:
        - "1-3:2-4"
```

Stahovač předá monitoru výsledná pravidla v doprovodném souboru
`<název XML>.filters.json`. Monitor zpracuje oba soubory a přesune je společně
do `watch/processed`; starší archiv stejného dne zachová v samostatné podsložce.
XML a jeho doprovodný soubor kopírujte společně. Ručně vložené XML bez tohoto
souboru použije aktuální uložená pravidla pro datum XML.
Vadný doprovodný soubor zpracování zastaví před změnou výstupů; po jeho opravě
monitor zpracování zkusí znovu. Čekající XML ani doprovodný soubor se nepřepíše.

🧾 Záznam manuální práce v prohlížeči (uloží JSON s požadavky):
```bash
$ (virt-env) ./so_recorder.py --output network_log.json --start-url "<libovolná stránka SkolaOnline>"
# provádějte akce v okně, pak v terminálu stiskněte Enter a log se uloží
```

##💡 **Tipy & Vylepšení** 
----------------------- 
- ⚙ **Automatizace:** Skripty lze spustit jako **cron job** nebo Windows Task Scheduler. 
- 📺 **TV Displej:** HTML výstup lze snadno zobrazit na **informační obrazovce**, nebo pomocí `feh` zobrazte obrázky
- 🔄 **Integrace s dalšími systémy:** Možnost úpravy výstupu pro školní web či digitální nástěnku. (CSS je přímo integrované v souboru)

## 🎯 Proč to používat?

- 🚀 Úspora času – automatické zpracování znamená méně ruční práce
- 📡 Aktualizace v reálném čase – stačí změnit soubor, výstup se vygeneruje
- 🎛 Flexibilita – výstup lze upravit pro různé potřeby školy

🔹 Naprogramováno s ❤️ pro učitelé, kteří potřebují méně chaosu ve svých suplováních!
