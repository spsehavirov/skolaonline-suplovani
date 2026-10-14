# 📢 Suplování ve ŠkolaOnline

![Python](https://img.shields.io/badge/python-3.13-blue?style=for-the-badge&logo=python)
![Status](https://img.shields.io/badge/status-active-brightgreen?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/spsehavirov/skolaonline-suplovani?style=for-the-badge)
![License](https://img.shields.io/github/license/spsehavirov/skolaonline-suplovani?style=for-the-badge)

Nástroje vzniklé z potřeby přizpůsobit suplování ze ŠkolaOnline pro školní TV ve vestibulu.
Žákovské výpisy lze stahovat přímo přes HTTP, bez Selenium a bez prohlížeče.

[![CI](https://github.com/spsehavirov/skolaonline-suplovani/actions/workflows/pylint.yml/badge.svg)](https://github.com/spsehavirov/skolaonline-suplovani/actions/workflows/pylint.yml)

## 🔧 Co už funguje

- 🌐 Přímé stahování žákovského suplování; k dispozici je i varianta přes Selenium.
- 👀 Sledování složky s XML, zpracování již přítomných souborů a archivace vstupů.
- 📄 Export žáků do CSV, HTML, PDF a PNG; export učitelů do CSV, HTML a PDF.
- 🎛️ Filtrování tříd, ročníků a hodin v žákovském výpisu, včetně výjimek pro konkrétní den.

## 🚀 Rychlý začátek

Příkazy spouštějte z kořene projektu. Instalátor používá **Python 3.13**;
potřebné systémové knihovny a podrobnosti jsou v [návodu k instalaci](docs/installation.md).

```bash
./install
source .venv/bin/activate
```

Po aktivaci uvidíte v terminálu označení `(.venv)`. Prostředí aktivujte v každém
novém terminálu, ze kterého budete skripty spouštět. V ukázkách `(.venv) $`
označuje prompt terminálu — zadávejte příkaz napravo od `$`.

🔑 Pro stahování vytvořte soubor `.env`:

```ini
SO_USER=vas-ucet-ve-skoleonline
SO_PASS=vase-heslo-pro-skoluonline
```

📡 V prvním, již aktivovaném terminálu spusťte monitor:

```console
(.venv) $ ./suplovani.py
```

🌍 Ve druhém terminálu aktivujte prostředí a stáhněte suplování pro vybraný den:

```console
$ source .venv/bin/activate
(.venv) $ ./so_soap.py --date "15.10.2026"
```

Monitor načte XML z `watch/`, vytvoří výpisy v `outputs/` a vstupy přesune do
`watch/processed/`. Oba stahovače a monitor automaticky použijí projektové `.venv`.
Další možnosti popisuje [návod k použití](docs/usage.md).

## 🎛️ Filtry

Například divadlo ve 2.–4. hodině pro ročníky 1–3 s úplným vynecháním třídy 3A:

```console
(.venv) $ ./so_soap.py --date "15.10.2026" --exclude=3A --skip=1-3:2-4
```

Parametry příkazu platí pouze pro stažené XML a nemění `config.yaml`.
Vyloučení třídy má přednost před ostatními pravidly.
[Úplný přehled filtrů a příklady](docs/filtering.md).

## 📚 Dokumentace

| Potřebuji… | Návod |
| --- | --- |
| 🔧 Nainstalovat projekt nebo vyřešit chybějící knihovny | [Instalace](docs/installation.md) |
| 🌐 Stahovat XML, spustit monitor nebo nastavit výstupy | [Použití a konfigurace](docs/usage.md) |
| 🎛️ Vynechat třídy či hodiny nebo nastavit denní výjimky | [Filtry](docs/filtering.md) |
| 🧪 Spustit testy, Pylint nebo nástroje pro vývoj | [Vývoj a ověřování](docs/development.md) |

<details>
<summary>🧭 Další nástroje, technické podklady a omezení</summary>

- `so_download.py` stahuje přes Selenium; [příklad spuštění](docs/usage.md#stahování-přes-selenium).
- `so_recorder.py` zaznamenává HTTP požadavky při ruční práci s prohlížečem;
  [použití záznamníku](docs/development.md#záznam-požadavků).
- [Architektura](docs/architecture.md), [struktura XML](docs/xml_structure.md)
  a [stručné shrnutí projektu](protocol.md) popisují současnou implementaci.
- [Audit závislostí](docs/dependency-security.md) zaznamenává kontrolu z 14. 10. 2026.
- [Návrh modernizace](modernisation.md) je pracovní plán; jeho navrhované funkce
  nejsou přehledem toho, co je už hotové. Přechod na Python 3.14 je odložený.
- Stahovaná sestava je zatím nastavená pro konkrétní školu. Její výběr pomocí
  přepínače není implementovaný; přímý stahovač používá formulář webové aplikace.

</details>

📄 Licence: [EUPL 1.2](LICENSE.md).

Naprogramováno s ❤️ pro učitele, kteří potřebují méně chaosu v suplování.
