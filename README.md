# Suplování ze ŠkolaOnline

Stažení a zpracování suplování ze ŠkolaOnline pro školní informační obrazovku.
Žákovské výpisy lze stahovat přímo přes HTTP, bez Selenium a bez prohlížeče.

[![CI](https://github.com/spsehavirov/skolaonline-suplovani/actions/workflows/pylint.yml/badge.svg)](https://github.com/spsehavirov/skolaonline-suplovani/actions/workflows/pylint.yml)

## Co funguje

- Přímé stahování žákovského suplování; k dispozici je i varianta přes Selenium.
- Sledování složky s XML, zpracování již přítomných souborů a archivace vstupů.
- Export žáků do CSV, HTML, PDF a PNG; export učitelů do CSV, HTML a PDF.
- Filtrování tříd, ročníků a hodin v žákovském výpisu, včetně výjimek pro konkrétní den.

## Rychlý začátek

Příkazy spouštějte z kořene projektu. Instalátor používá **Python 3.13**;
potřebné systémové knihovny a podrobnosti jsou v [návodu k instalaci](docs/installation.md).

```bash
./install
```

Pro stahování vytvořte soubor `.env`:

```ini
SO_USER=vas-ucet-ve-skoleonline
SO_PASS=vase-heslo-pro-skoluonline
```

V prvním terminálu spusťte monitor:

```bash
./suplovani.py
```

Ve druhém stáhněte suplování pro vybraný den:

```bash
./so_soap.py --date "15.10.2026"
```

Monitor načte XML z `watch/`, vytvoří výpisy v `outputs/` a vstupy přesune do
`watch/processed/`. Oba stahovače a monitor automaticky použijí projektové `.venv`.
Další možnosti popisuje [návod k použití](docs/usage.md).

## Filtry

Například divadlo ve 2.–4. hodině pro ročníky 1–3 s úplným vynecháním třídy 3A:

```bash
./so_soap.py --date "15.10.2026" --exclude=3A --skip=1-3:2-4
```

Parametry příkazu platí pouze pro stažené XML a nemění `config.yaml`.
Vyloučení třídy má přednost před ostatními pravidly.
[Úplný přehled filtrů a příklady](docs/filtering.md).

## Dokumentace

| Potřebuji… | Návod |
| --- | --- |
| Nainstalovat projekt nebo vyřešit chybějící knihovny | [Instalace](docs/installation.md) |
| Stahovat XML, spustit monitor nebo nastavit výstupy | [Použití a konfigurace](docs/usage.md) |
| Vynechat třídy či hodiny nebo nastavit denní výjimky | [Filtry](docs/filtering.md) |
| Spustit testy, Pylint nebo nástroje pro vývoj | [Vývoj a ověřování](docs/development.md) |

<details>
<summary>Další nástroje, technické podklady a omezení</summary>

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

Licence: [EUPL 1.2](LICENSE.md).
