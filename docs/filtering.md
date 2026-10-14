# Filtry tříd a hodin

[Zpět na hlavní stránku](../README.md) · [Použití stahovačů](usage.md)

Oba stahovače podporují stejné filtry. Uložená pravidla v `config.yaml` tvoří
základ; parametry příkazu se k nim přidají pro konkrétní stažené XML.
Příkaz **nemění `config.yaml` ani `.env`**.

## Přehled voleb

| Parametr | Význam | Výpis |
| --- | --- | --- |
| `--include=1A,1B` | Zahrnout vyjmenované třídy. | Žáci |
| `--exclude=3A` | Úplně vynechat třídu; má přednost i před include. | Žáci |
| `--hours=3-6` | Zobrazit jen hodiny 3 až 6. | Žáci |
| `--skip=2-4` | Vynechat hodiny 2 až 4 všem třídám. | Žáci |
| `--skip=1A:2-4` | Vynechat tyto hodiny třídě 1A. | Žáci |
| `--skip=1A,1B,1C:2-4` | Stejná výjimka pro několik tříd. | Žáci |
| `--skip=1-3:2-4` | Stejná výjimka pro všechny třídy ročníků 1–3. | Žáci |
| `--day-end-hour=5` | Omezit výpis nejvýše do 5. hodiny. | Žáci i učitelé |
| `--clear` | Ignorovat uložené include/exclude; ostatní filtry zachovat. | Konkrétní běh |
| `--no-config` | Ignorovat všechny uložené filtry; použít jen filtry příkazu. | Konkrétní běh |

`--hours` a `--skip` vynechávají všechny druhy záznamů ve vybraných hodinách,
včetně „odpadá“, suplování a změn učebny. Přehled absencí učitelů nemění.
`--no-config` dál používá provozní nastavení složek a formátů i přihlašovací údaje.

## Příklady

### Divadlo ve 2.–4. hodině

Pro ročníky 1–3 se tyto hodiny nezobrazí. Třída 3A je úplně vyloučená:

```bash
./so_soap.py --date "15.10.2026" --exclude=3A --skip=1-3:2-4
```

Výběr `1-3` zahrnuje 1A–3C i případná další oddělení, například 2D.
Pokud má výjimka platit jen pro konkrétní třídy, vypište jejich názvy.

### Výpis pouze od 3. do 6. hodiny

```bash
./so_soap.py --date "15.10.2026" --hours=3-6
```

Pro 1A lze současně vynechat 4. hodinu:

```bash
./so_soap.py --date "15.10.2026" --hours=3-6 --skip=1A:4
```

### Různé výjimky pro jednotlivé třídy

`--skip` lze opakovat:

```bash
./so_download.py --date "15.10.2026" --headless \
  --skip=1A:2-4 --skip=1B:1-2 --skip=1C:4
```

Stejná pravidla lze zapsat i společně:

```bash
./so_soap.py --date "15.10.2026" --skip=1A:2-4,1B:1-2,1C:4
```

Společná výjimka pro seznam tříd:

```bash
./so_soap.py --date "15.10.2026" --skip=1A,1B,1C:2-4
```

### Filtry pouze z příkazu

```bash
./so_soap.py --date "15.10.2026" --no-config --hours=3-6
```

## Jak se pravidla skládají

- Názvy tříd se porovnávají bez ohledu na velikost písmen.
- Uložené a zadané seznamy include/exclude se sjednotí. Neprázdný include
  vymezuje povolené třídy a exclude z nich vyloučené třídy odstraní.
- Rozmezí hodin se skládají průnikem, vynechávané hodiny sjednocením.
  Prázdný průnik znamená prázdný žákovský výpis.
- Uložený konec dne a `--day-end-hour` představují další horní mez;
  použije se nižší limit. V configu se používá `day_end_hour`, případně
  starší `day_end_period`, který má při současném zadání přednost.
- Vícehodinový záznam `1-6` po vynechání `2-4` vytvoří záznamy `1` a `5-6`.
  Filtry se použijí před slučováním záznamů, shodně pro CSV, HTML, PDF a PNG.
- Neznámé označení hodiny se zachová s upozorněním.

Jednotlivé hodiny a ročníky musí být kladné; rozsahy zahrnují oba kraje
a nesmějí být obrácené. Číselný výběr ročníku je jeden ročník nebo jeden rozsah;
seznam před dvojtečkou je seznam názvů tříd. Pro více různých výběrů ročníků
použijte opakované `--skip`.

## Uložené denní výjimky

Trvalé filtry upravujte přímo v `config.yaml`. Výjimky hodin patří pod konkrétní datum:

```yaml
settings:
  exclude: [3A]
  day_end_hour: 7
  student_filters_by_date:
    "2026-10-15":
      hours: "3-6"
      skip:
        - "1-3:2-4"
```

Datum pravidel se porovnává s datem uvnitř XML. Výjimka z tohoto příkladu
neovlivní jiný den. Nastavení polí jako `exclude` či `day_end_hour` platí
bez omezení data, dokud ho nezměníte nebo pro běh nepoužijete `--no-config`.

## Platnost pravidel a předání monitoru

Stahovač předá výsledná pravidla v souboru `<název XML>.filters.json`.
Monitor použije tento snapshot po celý export, i když mezitím změníte config.
Po zpracování archivuje oba soubory společně.

XML a jeho doprovodný soubor kopírujte společně. Ručně dodané XML bez tohoto
souboru použije aktuální uložená pravidla pro datum XML.
Čekající XML ani doprovodný soubor se při dalším stahování nepřepíše.

Vadný soubor filtrů nebo nesoulad názvu či data zastaví zpracování před změnou
výstupů. Vstupy zůstanou ve sledované složce a po opravě monitor zpracování zkusí znovu.

Oproti starším verzím se CLI filtry neukládají do configu. Pro další stažení
zadejte parametry znovu nebo přidejte odpovídající pravidla do `config.yaml`.
