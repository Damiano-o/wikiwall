# WikiWall

**Una voce di qualità di Wikipedia in italiano, diversa, sul tuo desktop Windows.**

![WikiWall](docs/screenshot.jpg)

WikiWall sceglie una voce dalla [Vetrina](https://it.wikipedia.org/wiki/Wikipedia:Vetrina) o dalle [Voci di qualità](https://it.wikipedia.org/wiki/Wikipedia:Voci_di_qualit%C3%A0) di Wikipedia in italiano, la impagina come una copertina editoriale e la usa come sfondo del desktop. Quando torni al computer, o quando apri il desktop, la voce cambia.

Non è un sito web aperto a tutto schermo: è un'immagine pulita e leggibile, pensata per essere guardata di sfuggita e per invogliarti ad aprire la voce completa.

## Caratteristiche

- **Solo voci di qualità**: la lista viene letta da `Wikipedia:Vetrina` e `Wikipedia:Voci di qualità`, non da `Speciale:Random`.
- **Niente ripetizioni**: le ultime 50 voci vengono evitate.
- **Più vetrina che qualità**: il 65% delle scelte arriva dalla Vetrina, il resto dalle Voci di qualità.
- **Aggiornamento automatico**: al login, quando torni da una pausa, quando compare il desktop e ogni 10 minuti.
- **Tema carta o tema scuro**, con titolo, descrizione, estratto della voce, immagine, QR code e attribuzione.
- **Fallback offline**: se Wikipedia non risponde, viene riusata l'ultima voce renderizzata.
- **Icona nella tray** con "Cambia ora", "Apri voce", "Pausa" ed "Esci".
- **Nessun servizio esterno**: tutto gira in locale; l'unica rete necessaria è quella verso Wikipedia.

## Requisiti

- Windows 10 o Windows 11
- Python 3.11 o successivo
- Connessione a Internet per scaricare nuove voci e immagini

## Installazione

Apri PowerShell nella cartella in cui vuoi clonare il progetto:

```powershell
git clone https://github.com/Damiano-o/wikiwall.git
cd wikiwall

python -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e .
python -m wikiwall setup
```

`wikiwall setup` installa Chromium per Playwright. Serve solo la prima volta (e quando Playwright viene aggiornato).

Se PowerShell blocca l'attivazione dell'ambiente:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Oppure usa il Python del virtualenv senza attivarlo:

```powershell
.venv\Scripts\python -m wikiwall next
```

### Primo sfondo

```powershell
python -m wikiwall next
```

La prima esecuzione scarica la lista delle voci di qualità e la mette in cache per 7 giorni. Poi sceglie una voce, scarica l'immagine e imposta lo sfondo.

### Avvio automatico

```powershell
python -m wikiwall install
```

Crea `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WikiWall.vbs`, che avvia `pythonw -m wikiwall watch` a ogni login. Per avviarlo subito, senza riavviare:

```powershell
python -m wikiwall watch
```

L'icona nella tray permette di cambiare subito la voce, aprirla nel browser, mettere in pausa il watcher o uscire.

Per rimuovere l'avvio automatico:

```powershell
python -m wikiwall uninstall
```

## Comandi

| Comando | Cosa fa |
| --- | --- |
| `python -m wikiwall next` | Sceglie una nuova voce e cambia subito lo sfondo |
| `python -m wikiwall next --no-set --output anteprima.png` | Genera solo l'immagine, senza toccare il desktop |
| `python -m wikiwall next --theme dark` | Genera con il tema scuro |
| `python -m wikiwall next --width 2560 --height 1440` | Forza una risoluzione diversa |
| `python -m wikiwall watch` | Avvia il watcher e l'icona nella tray |
| `python -m wikiwall watch --no-tray` | Avvia il watcher senza icona |
| `python -m wikiwall install` | Installa l'avvio automatico al login |
| `python -m wikiwall uninstall` | Rimuove l'avvio automatico |
| `python -m wikiwall config` | Mostra il file di configurazione |
| `python -m wikiwall config --open` | Apre la configurazione in Notepad |
| `python -m wikiwall history` | Mostra le ultime voci usate |
| `python -m wikiwall history --clear` | Svuota lo storico |
| `python -m wikiwall setup` | Installa Chromium per Playwright |

Se hai attivato il virtualenv, puoi usare `wikiwall` al posto di `python -m wikiwall`.

## Configurazione

Il file si trova in:

```text
%LOCALAPPDATA%\WikiWall\config.toml
```

Esempio:

```toml
# paper oppure dark
theme = "paper"

# Tempo massimo tra due cambi (minuti)
interval_minutes = 10

# Dopo quanti minuti di inattività, il ritorno al computer cambia la voce
idle_minutes = 5

# Distanza minima tra due cambi innescati dal desktop (minuti)
desktop_cooldown_minutes = 10

# Quante voci recenti evitare
history_size = 50

# Ogni quanti giorni riscaricare la lista delle voci di qualità
quality_cache_days = 7

# Facoltativo: forza una risoluzione (utile per test o monitor diversi)
# width = 2560
# height = 1440
```

Dopo una modifica, riavvia `wikiwall watch` (tray → Esci, poi di nuovo `python -m wikiwall watch`). Il comando `next` legge la configurazione aggiornata a ogni esecuzione.

## Come funziona

1. **Lista delle voci**: WikiWall interroga l'API di Wikipedia (`action=parse&prop=links`) sulle pagine `Wikipedia:Vetrina` e `Wikipedia:Voci di qualità`, tiene solo i link nel namespace principale e li mette in cache per 7 giorni.
2. **Scelta**: esclude le ultime voci usate, poi sceglie con una preferenza per la Vetrina (65%) rispetto alle Voci di qualità (35%).
3. **Contenuto**: scarica l'inizio della voce (`prop=extracts`, circa 1400 caratteri), la descrizione breve, l'immagine principale e l'URL.
4. **Impaginazione**: costruisce una pagina HTML con CSS, font di sistema e QR code, e la fotografa con Playwright Chromium alla risoluzione dello schermo.
5. **Sfondo**: imposta il PNG con `SystemParametersInfoW` e imposta lo stile "Riempi" (`WallpaperStyle=10`).
6. **Quando cambia**:
   - all'avvio del watcher (al login);
   - quando il desktop è in primo piano per almeno 3 secondi, con un cooldown configurabile;
   - quando torni al computer dopo `idle_minutes` di inattività;
   - ogni `interval_minutes` minuti;
   - quando premi "Cambia ora" nella tray.

## File e percorsi

Tutto viene salvato in `%LOCALAPPDATA%\WikiWall\`:

| File | Contenuto |
| --- | --- |
| `config.toml` | Configurazione |
| `wallpaper.png` | Ultimo sfondo generato |
| `history.json` | Ultime voci usate |
| `wikiwall.log` | Log del watcher |
| `cache\quality.json` | Lista delle voci di qualità |
| `cache\last_article.json` | Ultima voce, usata come fallback offline |

## Limitazioni

- **Solo Windows**: l'impostazione dello sfondo usa API Win32.
- **Solo monitor principale**: il PNG viene generato alla risoluzione dello schermo primario. Il supporto multi-monitor non è ancora incluso.
- **Immagine statica**: non è una pagina web interattiva; per leggere tutta la voce c'è il QR code o il comando "Apri voce" nella tray.
- **Internet**: la prima volta e a ogni nuova voce serve la rete. Se Wikipedia non risponde, WikiWall riusa l'ultima voce salvata.
- **Lista di qualità**: se Wikipedia cambia la struttura delle pagine `Wikipedia:Vetrina` o `Wikipedia:Voci di qualità`, il parser potrebbe dover essere aggiornato.

## Sviluppo

```powershell
python -m pip install -e ".[dev]"
pytest -q
ruff check .
```

Struttura del progetto:

```text
src/wikiwall/
  wikipedia.py   API Wikipedia, lista di qualità, scelta della voce
  template.py    HTML e CSS della copertina
  render.py      rendering con Playwright
  wallpaper.py   sfondo Windows, inattività, desktop in primo piano
  core.py        orchestrazione: scegli → renderizza → imposta
  watcher.py     ciclo automatico e trigger
  tray.py        icona e menu nella tray
  startup.py     avvio automatico al login
  cli.py         comandi da terminale
tests/           test unitari
```

## Licenza e attribuzione

Il codice di WikiWall è distribuito con licenza **MIT** (vedi [LICENSE](LICENSE)).

I testi e le immagini delle voci provengono da **Wikipedia** e sono distribuiti con licenza **CC BY-SA 4.0**, salvo diversa indicazione. L'attribuzione è riportata nello sfondo stesso:

> Testo e immagini: Wikipedia · CC BY-SA 4.0

WikiWall non è affiliato alla Wikimedia Foundation. Wikipedia è un marchio della Wikimedia Foundation.

Lo screenshot di esempio mostra la voce [La grande onda di Kanagawa](https://it.wikipedia.org/wiki/La_grande_onda_di_Kanagawa); l'opera raffigurata è di Katsushika Hokusai ed è nel pubblico dominio.

## Crediti

- [Wikipedia](https://it.wikipedia.org) e [Wikimedia Commons](https://commons.wikimedia.org) per contenuti e API.
- [Playwright](https://playwright.dev/python/) per il rendering HTML.
- [Pillow](https://python-pillow.org/), [pystray](https://github.com/moses-palmer/pystray) e [qrcode](https://github.com/lincolnloop/python-qrcode) per immagine, tray e QR.
- Ispirato all'idea di avere ogni giorno una pagina diversa da leggere, senza aprire il browser.
