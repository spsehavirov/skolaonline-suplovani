# Vývoj a ověřování

[Zpět na hlavní stránku](../README.md)

## Testy a Pylint

Po [instalaci](installation.md) spusťte z kořene projektu:

```bash
.venv/bin/python -m pip check
.venv/bin/python -m unittest discover -s tests -v
```

Testy používají syntetická XML a dočasné složky. Ověřují filtry, předávání pravidel
mezi stahovačem a monitorem, archivaci a skutečné CSV/PDF/PNG exporty.
Neprovádějí přihlášení ani živé stahování ze ŠkolaOnline.

Pylint pro lokální kontrolu nainstalujte z připnutých CI závislostí:

```bash
.venv/bin/python -m pip install -r requirements-ci.txt
.venv/bin/python -m pylint --py-version=3.13 $(git ls-files '*.py')
```

GitHub Actions vytváří samostatné `.venv` pro Python 3.12 a 3.13 a na obou
spouští kontrolu závislostí, Pylint a regresní testy. Matice nepoužívá lokální
`./install`, který zůstává zaměřený na Python 3.13.

Pro ověření na jiné verzi použijte samostatný checkout a prostředí pro danou verzi,
aby projektové `.venv` nepřesměrovalo přímé spuštění na jiný interpreter.

## Audit závislostí

Postup kontroly pomocí `pip-audit` a výsledky aktualizace z 14. 10. 2026 jsou v
[záznamu auditu](dependency-security.md). Výsledek auditu platí k datu kontroly;
při další aktualizaci závislostí kontrolu zopakujte.

## Záznam požadavků

`so_recorder.py` je pomocný nástroj pro zjišťování průběhu webových požadavků.
Otevře přihlášený Chrome a po ukončení ruční práce uloží záznam do JSON.
Před spuštěním potřebuje přihlašovací údaje v `.env`.

```bash
.venv/bin/python so_recorder.py --output network_log.json
```

V prohlížeči proveďte potřebné kroky a potom v terminálu stiskněte Enter.
Jinou počáteční stránku lze vybrat pomocí `--start-url`.
Záznamník nepoužívá automatický přechod do projektového `.venv`, proto je
v příkladu uvedený interpreter explicitně.

## Technické podklady a plány

- [Architektura](architecture.md) popisuje tok dat a hlavní moduly.
- [Struktura XML](xml_structure.md) mapuje údaje ŠkolaOnline na pole výpisu.
- [Shrnutí projektu](../protocol.md) poskytuje stručný technický přehled.
- [Návrh modernizace](../modernisation.md) obsahuje náměty pro budoucí práci,
  nikoli implementované funkce nebo závaznou verzi instalace.

Stahovače mají adresu a ID konkrétní sestavy ve svých konstantách. Přímé HTTP
stahování pracuje s formulářem webové aplikace, takže případná změna formuláře
může vyžadovat úpravu stahovače. Samostatná volba sestavy přes CLI zatím chybí.
