# Suplování ve ŠkolaOnline

Tato sada skriptů vznikla na základě potřeby přizpůsobit si export dat z ŠO pro suplování (a následné zobrazení na TV ve vestibulu školy). Protože ŠO nenabízí API,
je potřeba ze stránky stáhnout XML soubor a ten zpracovat.

## ./suplovani.py

Tento skript monitoruje složku (výchozí: `./watch`) a podud se tam oběví požadovaný formát (XML pro žáky nebo učitelé) tak ho zpracuje do CSV, HTML a PDF

## ./so_download.py

Tento skript umožnuje stažení ze školy online pomocí automatizovaného prohlížeče

## Použití

Pro správné použití je potřeba vytvořit soubor `.env` a do něho nahrát tyto údaje:

```ini
SO_USER=<vas-ucet-ve-skoleonline>
SO_PASS=<vase-heslo-pro-skoluonline>
```

```bash
$ ./install
$ source bin/activate
$ (virt-env) ./suplovani.py # Zapne monitorování složky

$ (virt-env) ./so_download.py --date "20.2.2025" --headless # Stáhne data k požadovaného datu
```
