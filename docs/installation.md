# Instalace

[Zpět na hlavní stránku](../README.md)

## Python a prostředí

Lokální instalátor používá Python **3.13**, který je současným cílem i pro provoz
na Raspberry Pi. GitHub Actions ověřuje kompatibilitu na Pythonu 3.12 a 3.13;
přechod na Python 3.14 zatím není součástí instalace.

Ověřte dostupnost interpreteru:

```bash
python3.13 --version
```

<details>
<summary>Python na macOS</summary>

Při použití Homebrew:

```bash
brew install python@3.13
```

</details>

## Knihovny pro PDF a PNG

PDF vytváří WeasyPrint, které kromě Python balíčků potřebuje systémové knihovny
Pango. PNG vzniká následným převodem PDF.

<details>
<summary>Debian, Ubuntu a Raspberry Pi OS</summary>

Pro instalaci přes pip s dostupnými wheels:

```bash
sudo apt-get update
sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
```

Python 3.13 musí být nainstalovaný samostatně. Pokud pip na dané architektuře
sestavuje balíčky ze zdrojů, může být potřeba doplnit vývojové knihovny.
Podrobnosti pro jednotlivé distribuce uvádí
[instalační návod WeasyPrint](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).

</details>

<details>
<summary>macOS</summary>

WeasyPrint ve svém návodu doporučuje instalaci přes Homebrew, která dodá i systémové závislosti:

```bash
brew install weasyprint
```

Projekt potom nainstaluje vlastní připnutou verzi Python balíčku do `.venv`.
Další možnosti a řešení chyb s hledáním knihoven popisuje
[návod WeasyPrint](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#macos).

</details>

## Instalace projektu

Z kořene projektu spusťte:

```bash
./install
source .venv/bin/activate
```

Instalátor vytvoří `.venv` a nainstaluje závislosti z `requirements.txt`.
`so_soap.py`, `so_download.py` a `suplovani.py` při přímém spuštění automaticky
použijí toto prostředí. Aktivace je přesto součástí doporučeného postupu pro práci
v terminálu: zajistí stejné prostředí i pro další příkazy `python` a `pip`.

Po aktivaci se v promptu obvykle objeví `(.venv)`. Prostředí aktivujte v každém
novém terminálu. Ukázky s `(.venv) $` označují aktivované prostředí;
do terminálu zadávejte příkaz napravo od `$`.

Bez projektového `.venv` zůstane použitý interpreter aktuálního prostředí,
například u staršího nasazení na Raspberry Pi.

Pro stahování vytvořte `.env` s přihlašovacími údaji:

```ini
SO_USER=vas-ucet-ve-skoleonline
SO_PASS=vase-heslo-pro-skoluonline
```

Samotné zpracování ručně dodaného XML přihlášení nepotřebuje.
Pokračujte [spuštěním monitoru a stažením XML](usage.md).

## Řešení běžných chyb

| Chyba | Postup |
| --- | --- |
| `Python 3.13 is required` | Nainstalujte nebo zpřístupněte `python3.13`, poté spusťte `./install`. |
| `ModuleNotFoundError` | Spusťte `./install`; případně použijte `.venv/bin/python so_soap.py …`. |
| `.venv` používá jinou verzi Pythonu | Přesuňte staré prostředí, například `mv .venv .venv.bak`, a znovu spusťte instalátor. |
| `cannot load library` při importu WeasyPrint | Zkontrolujte systémové knihovny Pango podle návodu výše. |
| `Missing SO_USER or SO_PASS` | Doplňte obě hodnoty do `.env` v kořeni projektu. |

Kontrolu instalace a exportů popisuje [návod k ověřování](development.md#testy-a-pylint).
