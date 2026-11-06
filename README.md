# Pflanzophon – KI-Telefon-Assistent (Raspberry Pi + ElevenLabs)

Ein altes Telefon mit USB-Hörer wird zum KI-Gesprächspartner: Hörer abheben → ElevenLabs
Conversational-AI-Agent meldet sich. Hörer auflegen → Gespräch endet.

## Dateien

| Datei | Zweck |
|---|---|
| `telefon_assistant.py` | Hauptprogramm (GPIO-Hörerschalter + Taste `a` im Terminal) |
| `audio_test.py` | Prüft, ob Mikrofon/Lautsprecher mit 16000 Hz geöffnet werden können |
| `config/asound.conf` | ALSA-Konfiguration für den USB-Hörer → kommt nach `/etc/asound.conf` |
| `requirements.txt` | Python-Abhängigkeiten |
| `.env.example` | Vorlage für API-Key und Agent-ID (→ `.env`) |

## Hardware

- Raspberry Pi 5 / Edge-Box (Hostname `Pflanzophon01`, Benutzer `drjakob`)
- USB-Audio-Hörer (`card 2: Device [USB Audio Device]`)
- Gabelschalter des Hörers an **GPIO 17** und GND (gpiozero `Button`, interner Pull-up)

## Installation auf dem Pi

```bash
sudo apt update && sudo apt install -y python3-venv portaudio19-dev alsa-utils libasound2-plugins swig liblgpio-dev lgpio
```

```bash
mkdir -p ~/telefon_assistent && cd ~/telefon_assistent
```

Dateien vom Mac auf den Pi kopieren (auf dem **Mac** im Projektordner ausführen):

```bash
scp telefon_assistant.py audio_test.py requirements.txt .env.example .env config/asound.conf drjakob@Pflanzophon01.local:~/telefon_assistent/
```

Auf dem Pi:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

Falls noch keine `.env` kopiert wurde:

```bash
cp .env.example .env && nano .env
```

## Fehler „Invalid sample rate“ – Ursache und Lösung

### Symptom

```
Expression 'paInvalidSampleRate' failed in 'src/hostapi/alsa/pa_linux_alsa.c'
Error running conversation: [Errno -9997] Invalid sample rate
Session beendet. ID: None
```

### Ursache

- Das `DefaultAudioInterface` von ElevenLabs öffnet Mikrofon **und** Lautsprecher mit
  **16000 Hz, Mono, 16 Bit**.
- Der USB-Hörer kann hardwareseitig meist nur **44100 oder 48000 Hz**.
- Eine `/etc/asound.conf` mit `type hw` reicht die Anfrage **ohne Umrechnung** direkt an die
  Hardware durch → die Hardware lehnt 16000 Hz ab → `Invalid sample rate`.
- Die Meldung `capture slave is not defined` zeigt außerdem, dass in einer früheren
  `asound.conf` ein `asym`-Gerät ohne Aufnahme-Teil eingetragen war.

### Lösung: `plug`-Gerät statt `hw`

`config/asound.conf` nutzt `plughw`, das Abtastrate, Format und Kanalzahl automatisch
umrechnet, und spricht die Karte über ihren **Namen** (`Device`) statt über die Nummer an
(die Nummer kann sich nach einem Neustart ändern):

```bash
sudo cp ~/telefon_assistent/asound.conf /etc/asound.conf
```

Kartenname prüfen (steht nach `card 2:`):

```bash
arecord -l
```

Steht dort etwas anderes als `Device`, in `/etc/asound.conf` beide `CARD=Device` bzw.
`card Device` anpassen.

### Testen

```bash
python audio_test.py
```

Erwartet:

```
OK:     Mikrofon lässt sich mit 16000 Hz öffnen.
OK:     Lautsprecher lässt sich mit 16000 Hz öffnen.
```

Zusätzlicher Hardware-Test (5 s aufnehmen, dann abspielen):

```bash
arecord -r 16000 -f S16_LE -c 1 -d 5 test.wav && aplay test.wav
```

### Harmlose Meldungen

Die vielen `ALSA lib ... Unknown PCM surround51/iec958/modem ...` sowie
`jack server is not running` erscheinen beim Start von PortAudio immer, weil es alle
denkbaren Geräte abfragt. Sie sind **keine** Fehler. Entscheidend ist nur die letzte Zeile.

### Weitere Fehler

| Meldung | Ursache |
|---|---|
| `401 Unauthorized` | Falscher/alter API-Key in `.env` oder Key ohne Berechtigung für Conversational AI |
| `Invalid sample rate` | `/etc/asound.conf` nutzt `hw` statt `plug` (siehe oben) |
| `Device unavailable` / `Device or resource busy` | Ein anderes Programm (z. B. ein zweiter Start des Skripts) nutzt den Hörer |

## Klang verbessern („blechern“)

Ursachen, nach Wirkung sortiert:

1. **Einfache Abtastraten-Umrechnung:** ElevenLabs liefert 16000 Hz, der Hörer läuft mit
   44100/48000 Hz. ALSA rechnet standardmäßig mit dem groben `linear`-Verfahren um.
   `config/asound.conf` nutzt deshalb `speexrate_best`. Dafür muss dieses Paket installiert sein:

   ```bash
   sudo apt install -y libasound2-plugins
   ```

   ```bash
   sudo cp ~/telefon_assistent/asound.conf /etc/asound.conf
   ```

2. **Übersteuerung:** Steht die Lautstärke des USB-Hörers auf 100 %, verzerrt der kleine
   Lautsprecher. In `alsamixer` mit `F6` die Karte „USB Audio Device“ wählen und
   *Speaker* auf ca. 70–80 % stellen, das Mikrofon („Mic“) ebenfalls nicht auf Maximum
   (sonst übersteuert die Spracherkennung). Dauerhaft speichern:

   ```bash
   alsamixer
   ```

   ```bash
   sudo alsactl store
   ```

3. **Stimme im ElevenLabs-Agenten:** Im Agent-Dashboard unter *Voice* eine wärmere Stimme
   bzw. ein höherwertiges TTS-Modell wählen und *Stability* etwas erhöhen. Das
   Ausgabeformat muss **PCM 16000 Hz** bleiben, sonst spielt das Skript die Stimme zu
   schnell oder zu langsam ab.

4. **Grenze der Hardware:** Telefonhörer-Lautsprecher geben kaum Bässe wieder – ein
   gewisser „Telefonklang“ ist normal und passt zum Pflanzophon.

## Starten

```bash
source ~/telefon_assistent/.venv/bin/activate && python ~/telefon_assistent/telefon_assistant.py
```

- **Hörer abheben** oder `a` + Enter → Gespräch startet
- **Hörer auflegen** oder `q` + Enter → Gespräch endet
- `Strg+C` → Programm beenden

## Autostart (systemd)

Datei `/etc/systemd/system/telefon_ki.service` anlegen:

```ini
[Unit]
Description=Telefon KI Assistent
After=network-online.target sound.target
Wants=network-online.target

[Service]
ExecStart=/home/drjakob/telefon_assistent/.venv/bin/python /home/drjakob/telefon_assistent/telefon_assistant.py
WorkingDirectory=/home/drjakob/telefon_assistent
Environment="GPIOZERO_PIN_FACTORY=lgpio"
Environment="PYTHONUNBUFFERED=1"
User=drjakob
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Aktivieren und Log ansehen:

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now telefon_ki.service
```

```bash
journalctl -u telefon_ki.service -f
```

Im Autostart gibt es kein Terminal – die Taste `a` funktioniert dort nicht, nur der Hörer.

## Datei auf dem Pi löschen und neu anlegen

```bash
rm ~/telefon_assistent/telefon_assistant.py
```

Dann entweder neu vom Mac kopieren (siehe `scp` oben) oder im Editor neu anlegen und Inhalt
einfügen (Speichern: `Strg+O`, Enter, Beenden: `Strg+X`):

```bash
nano ~/telefon_assistent/telefon_assistant.py
```

## Sicherheit

Die `.env` mit dem API-Key **nicht** in Git oder geteilte Ordner legen – nur `.env.example`.
