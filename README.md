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
```bash
$ ./install
$ source bin/activate
```
(`install` nainstaluje i `requests-toolbelt`, kterou používá `so_soap.py` pro multipart/form-data volání.)
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
(`so_soap.py` sdílí stejné volby `--include/--exclude/--clear` a ukládá výstupy se stejným názvem jako Selenium varianta.)
(`--day-end-hour` nastaví `settings.day_end_hour` v `config.yaml` a omezí výpis suplování jen do zadané hodiny.)

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
