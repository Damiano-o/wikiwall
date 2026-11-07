# WikiWall

[![CI](https://github.com/Damiano-o/wikiwall/actions/workflows/ci.yml/badge.svg)](https://github.com/Damiano-o/wikiwall/actions/workflows/ci.yml)

**Una voce di qualità di Wikipedia in italiano, diversa, sul tuo desktop Windows.**

![WikiWall](docs/screenshot.jpg)

WikiWall sceglie una voce dalla [Vetrina](https://it.wikipedia.org/wiki/Wikipedia:Vetrina) o dalle [Voci di qualità](https://it.wikipedia.org/wiki/Wikipedia:Voci_di_qualit%C3%A0) di Wikipedia in italiano, la impagina come una copertina editoriale e la usa come sfondo del desktop. Quando torni al computer, o quando apri il desktop, la voce cambia.

Non è un sito web aperto a tutto schermo: è un'immagine pulita e leggibile, pensata per essere guardata di sfuggita e per invogliarti ad aprire la voce completa. Il QR e l'indirizzo della voce sono cliccabili quando la zona non è coperta da altre finestre.

## Caratteristiche

- **Solo voci di qualità**: la lista viene letta da `Wikipedia:Vetrina` e `Wikipedia:Voci di qualità`, non da `Speciale:Random`.
- **Niente ripetizioni**: le ultime 50 voci vengono evitate.
- **Più vetrina che qualità**: il 65% delle scelte arriva dalla Vetrina, il resto dalle Voci di qualità.
- **Aggiornamento automatico**: al login, quando torni da una pausa, quando compare il desktop e ogni 10 minuti.
- **QR e link cliccabili**: le zone del QR, dell'indirizzo e del pulsante "Salta voce" sono già attive appena compare il desktop, quindi il primo clic arriva sempre. Si nascondono quando un'altra applicazione prende il focus, così non rubano clic alle finestre.
- **Salta voce**: il pulsante sullo sfondo, la voce nella tray e la scorciatoia `Ctrl+Alt+N` passano subito alla voce successiva.
- **Interruttore acceso/spento**: "Spegni WikiWall" nella tray (o `wikiwall off`) ferma ogni cambio e lascia lo sfondo che hai in quel momento; "Accendi WikiWall" lo riattiva. La scelta resta salvata anche dopo un riavvio.
- **Tema carta o tema scuro**, con titolo, descrizione, estratto della voce, immagine, QR code e attribuzione. Il QR resta scuro su carta chiara in entrambi i temi, così lo leggono tutti gli scanner.
- **Cambio tema da terminale**: `wikiwall theme dark --apply` cambia e applica subito.
- **Un solo processo**: se il watcher è già attivo, un secondo `watch` si ferma subito invece di duplicare overlay e tray.
- **Tipografia editoriale**: Source Serif 4 per il testo e Montserrat per i dettagli, con un lead più grande e un estratto più breve.
- **Layout fluido**: si adatta a 1920×1200, 1366×768 e 800×600 senza perdere leggibilità.
- **Fallback offline**: se Wikipedia non risponde, viene riusata l'ultima voce renderizzata.
- **Icona nella tray** con "Cambia ora", "Salta voce", "Apri voce", "QR e link cliccabili", l'interruttore acceso/spento ed "Esci". Quando è spento, l'icona diventa grigia.
- **Nessun servizio esterno**: tutto gira in locale; l'unica rete necessaria è quella verso Wikipedia.

## Novità 0.4.0

- **Pulsante per accendere e spegnere WikiWall**: la voce nella tray diventa "Spegni WikiWall" / "Accendi WikiWall", l'icona si spegne e il menu grigia le azioni non disponibili. Da terminale: `wikiwall off`, `wikiwall on`, `wikiwall toggle`, `wikiwall status`.
- **Lo stato sopravvive al riavvio**: la scelta è in `state.json`, quindi se spegni WikiWall non riparte al login finché non lo riaccendi.
- **Quando è spento lo sfondo resta tuo**: nessun cambio automatico e nessun QR cliccabile sopra l'immagine; il watcher continua a girare in tray per riaccendersi al volo.
- **Scorciatoia `Ctrl+Alt+O`** per accendere e spegnere senza aprire la tray. Se è occupata, WikiWall lo segnala e continua con le altre due.

- **Clic che funzionano al primo colpo**: le zone cliccabili esistono già appena il desktop è in primo piano, non vengono più create al passaggio del mouse. Prima un clic veloce poteva finire sul desktop e non fare nulla.
- **Niente più doppioni**: il watcher tiene un lock, quindi due istanze non si contendono overlay, tray e scorciatoia.
- **Tema scuro rifinito** e QR sempre leggibile: moduli scuri su carta chiara anche con il tema nero.
- **`wikiwall theme`** per vedere o cambiare tema, con `--apply` per aggiornare subito lo sfondo.
- **Immagine di copertina**: se la foto della voce non carica, resta l'iniziale invece di un pannello vuoto.
- **`--no-set`** scrive l'anteprima in `cache/preview.png` e non tocca più lo sfondo attuale.
- `Ctrl+Alt+N` e "Salta voce" restano reattivi anche durante un cambio in corso.

## Novità 0.2.1

- Il pulsante "Salta voce" e gli hotspot ora funzionano anche quando un'altra applicazione è in primo piano, purché la zona non sia coperta da una finestra.

## Novità 0.2.0

- QR e link cliccabili sopra lo sfondo, senza rubare il focus alle altre applicazioni.
- Pulsante "Salta voce" sullo sfondo, nella tray e scorciatoia globale `Ctrl+Alt+N`.
- Restyling con i font open source del brand Wikimedia, gerarchia lead/estratto e layout fluido.
- Nuova etichetta del QR e URL più evidente.

![Tema scuro](docs/screenshot-dark.jpg)

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

Il comando `next` imposta solo lo sfondo. Per avere anche QR e link cliccabili, salta voce e aggiornamento automatico, avvia il watcher:

```powershell
python -m wikiwall watch
```

### Avvio automatico

```powershell
python -m wikiwall install
```

Crea `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WikiWall.vbs`, che avvia `pythonw -m wikiwall watch` a ogni login. Per avviarlo subito, senza riavviare:

```powershell
python -m wikiwall watch
```

L'icona nella tray permette di cambiare subito la voce, saltarla, aprirla nel browser, disattivare il QR cliccabile, spegnere o accendere WikiWall, o uscire. Per congelare lo sfondo che hai scelto:

```powershell
python -m wikiwall off
```

Il watcher continua a girare in tray, ma non tocca più lo sfondo. Per riprendere:

```powershell
python -m wikiwall on
```

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
| `python -m wikiwall watch` | Avvia watcher, tray, QR cliccabile e hotkey |
| `python -m wikiwall watch --no-overlay` | Avvia il watcher senza QR e link cliccabili |
| `python -m wikiwall watch --no-tray` | Avvia il watcher senza icona |
| `python -m wikiwall install` | Installa l'avvio automatico al login |
| `python -m wikiwall uninstall` | Rimuove l'avvio automatico |
| `python -m wikiwall config` | Mostra il file di configurazione |
| `python -m wikiwall config --open` | Apre la configurazione in Notepad |
| `python -m wikiwall history` | Mostra le ultime voci usate |
| `python -m wikiwall history --clear` | Svuota lo storico |
| `python -m wikiwall theme` | Mostra il tema attivo |
| `python -m wikiwall theme dark --apply` | Passa al tema scuro e aggiorna subito lo sfondo |
| `python -m wikiwall setup` | Installa Chromium per Playwright |
| `python -m wikiwall off` | Spegne WikiWall e lascia lo sfondo attuale |
| `python -m wikiwall on` | Riaccende WikiWall |
| `python -m wikiwall toggle` | Inverte lo stato |
| `python -m wikiwall status` | Mostra se WikiWall è acceso e se il watcher gira |

Se hai attivato il virtualenv, puoi usare `wikiwall` al posto di `python -m wikiwall`.

## Scorciatoie

| Scorciatoia | Azione |
| --- | --- |
| `Ctrl+Alt+N` | Salta alla voce successiva |
| `Ctrl+Alt+O` | Accende o spegne WikiWall |
| Clic sul QR | Apre la voce su Wikipedia |
| Clic sull'indirizzo della voce | Apre la voce su Wikipedia |
| Clic su "Salta voce" | Passa alla voce successiva |

La scorciatoia è globale: funziona anche quando un'altra applicazione è in primo piano. Se `Ctrl+Alt+N` è già usata da un altro programma, WikiWall lo segnala nel log e lascia disponibili il pulsante sullo sfondo e la voce nella tray.

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

# QR e link cliccabili sopra lo sfondo
clickable_qr = true

# Facoltativo: forza una risoluzione (utile per test o monitor diversi)
# width = 2560
# height = 1440
```

Dopo una modifica, riavvia `wikiwall watch` (tray → Esci, poi di nuovo `python -m wikiwall watch`). Il comando `next` legge la configurazione aggiornata a ogni esecuzione.

## Come funziona

1. **Lista delle voci**: WikiWall interroga l'API di Wikipedia (`action=parse&prop=links`) sulle pagine `Wikipedia:Vetrina` e `Wikipedia:Voci di qualità`, tiene solo i link nel namespace principale e li mette in cache per 7 giorni.
2. **Scelta**: esclude le ultime voci usate, poi sceglie con una preferenza per la Vetrina (65%) rispetto alle Voci di qualità (35%).
3. **Contenuto**: scarica l'inizio della voce (`prop=extracts`), la descrizione breve, l'immagine principale e l'URL.
4. **Impaginazione**: costruisce una pagina HTML con CSS, font incorporati, lead, estratto e QR code, e la fotografa con Playwright Chromium alla risoluzione dello schermo.
5. **Sfondo**: imposta il PNG con `SystemParametersInfoW` e imposta lo stile "Riempi" (`WallpaperStyle=10`).
6. **Interazione**: un piccolo overlay Tkinter senza cornice copre solo il QR, l'URL e il pulsante "Salta voce". Le zone sono attive finché il desktop è in primo piano e si nascondono quando un'altra applicazione prende il focus; usano `WS_EX_NOACTIVATE` per non rubare il focus. Un clic apre il browser o salta la voce.
7. **Quando cambia**:
   - all'avvio del watcher (al login);
   - quando il desktop è in primo piano per almeno 3 secondi, con un cooldown configurabile;
   - quando torni al computer dopo `idle_minutes` di inattività;
   - ogni `interval_minutes` minuti;
   - quando premi "Cambia ora" o "Salta voce" nella tray, o `Ctrl+Alt+N`.

## File e percorsi

Tutto viene salvato in `%LOCALAPPDATA%\WikiWall\`:

| File | Contenuto |
| --- | --- |
| `config.toml` | Configurazione |
| `wallpaper.png` | Ultimo sfondo generato |
| `history.json` | Ultime voci usate |
| `wikiwall.log` | Log del watcher |
| `state.json` | Stato acceso/spento, rispettato anche dopo un riavvio |
| `cache\quality.json` | Lista delle voci di qualità |
| `cache\last_article.json` | Ultima voce, usata come fallback offline |

I font sono inclusi nel pacchetto, in `src/wikiwall/assets/fonts/`.

## Limitazioni

- **Solo Windows**: l'impostazione dello sfondo e l'overlay usano API Win32.
- **Solo monitor principale**: il PNG viene generato alla risoluzione dello schermo primario. Il supporto multi-monitor non è ancora incluso.
- **Overlay sopra lo sfondo**: QR, link e pulsante "Salta voce" sono cliccabili quando il desktop è in primo piano e il watcher è in esecuzione. Quando un'applicazione prende il focus le zone si nascondono, per non intercettare i suoi clic.
- **Hotkey**: se `Ctrl+Alt+N` è occupata da un altro programma, restano disponibili il pulsante sullo sfondo e la tray.
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
  template.py    HTML e CSS della copertina, font e QR
  render.py      rendering con Playwright e coordinate dei bersagli cliccabili
  wallpaper.py   sfondo Windows, inattività, desktop in primo piano
  core.py        orchestrazione: scegli → renderizza → imposta
  watcher.py     ciclo automatico, trigger e interazione
  overlay.py     QR, link e "Salta voce" cliccabili
  hotkey.py      scorciatoia globale Ctrl+Alt+N
  single_instance.py  lock che impedisce due watcher contemporanei
  tray.py        icona e menu nella tray
  startup.py     avvio automatico al login
  cli.py         comandi da terminale
  assets/fonts/  Montserrat e Source Serif 4 (OFL)
tests/           test unitari
```

## Licenza e attribuzione

Il codice di WikiWall è distribuito con licenza **MIT** (vedi [LICENSE](LICENSE)).

I testi e le immagini delle voci provengono da **Wikipedia** e sono distribuiti con licenza **CC BY-SA 4.0**, salvo diversa indicazione. L'attribuzione è riportata nello sfondo stesso:

> Testo e immagini: Wikipedia · CC BY-SA 4.0

WikiWall non è affiliato alla Wikimedia Foundation. Wikipedia è un marchio della Wikimedia Foundation.

I font [Montserrat](https://github.com/JulietaUla/Montserrat) e [Source Serif 4](https://github.com/adobe-fonts/source-serif) sono distribuiti con licenza **SIL Open Font License 1.1**; le licenze sono incluse in `src/wikiwall/assets/fonts/`.

Lo screenshot chiaro mostra la voce [La grande onda di Kanagawa](https://it.wikipedia.org/wiki/La_grande_onda_di_Kanagawa); l'opera raffigurata è di Katsushika Hokusai ed è nel pubblico dominio. Lo screenshot scuro mostra il [Colosseo](https://it.wikipedia.org/wiki/Colosseo).

## Crediti

- [Wikipedia](https://it.wikipedia.org) e [Wikimedia Commons](https://commons.wikimedia.org) per contenuti e API.
- [Playwright](https://playwright.dev/python/) per il rendering HTML.
- [Pillow](https://python-pillow.org/), [pystray](https://github.com/moses-palmer/pystray) e [qrcode](https://github.com/lincolnloop/python-qrcode) per immagine, tray e QR.
- [Montserrat](https://github.com/JulietaUla/Montserrat) e [Source Serif 4](https://github.com/adobe-fonts/source-serif) per la tipografia.
- Ispirato all'idea di avere ogni giorno una pagina diversa da leggere, senza aprire il browser.
