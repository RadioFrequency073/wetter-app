# Wetter-App für Raspberry Pi 4 (Open-Meteo + PySide6)

Eine Wetter-App, die Daten der kostenlosen [Open-Meteo API](https://open-meteo.com)
(kein API-Key nötig, kostenlos für nicht-kommerzielle Nutzung) grafisch auf
einem HDMI-Monitor/TV anzeigt.

## Funktionen

- **Aktuell-Karte**: Temperatur, gefühlte Temperatur, Wetter-Icon, Wind,
  Luftfeuchte, Niederschlag der letzten Stunde
- **Stunden-Chart**: Temperaturverlauf + Regensummen der nächsten 24 Stunden
  (6-48 h einstellbar), als Matplotlib-Diagramm
- **16-Tage-Übersicht**: Tabelle mit Wettercode, Min/Max, Regensumme,
  Regenwahrscheinlichkeit, Wind, UV-Index
- **Details-Karte**: UV-Index (jetzt + Tagesmax), Luftdruck,
  Sonnenauf-/untergang, Böen
- **Ortssuche** über die Open-Meteo Geocoding API (Suchfeld oben,
  Vorschläge beim Tippen, Auswahl speichert den Ort)
- **Einstellungsdialog**: Aktualisierungsintervall, Anzahl Tage (1-16) und
  Stunden, Temperatureinheit (°C/°F), Ein-/Ausschalten jedes Inhaltsblocks,
  Vollbild beim Start
- Datenabruf im Hintergrund-Thread, Auto-Refresh per Timer,
  Wiederholung bei Netzwerkfehlern
- Vollbild per **F11** oder **Esc** umschaltbar

## Installation auf dem Raspberry Pi 4

Die App installiert ihre Pakete **selbst** beim allerersten Aufruf
(`bootstrap.py`): Fehlende Pakete werden per `pip` nachinstalliert; schlägt
das fehl (Raspberry Pi OS Bookworm erzwingt PEP 668, und auf 32-Bit-OS gibt
es keine PySide6-Wheels), fällt sie automatisch auf `sudo apt install
python3-pyside6 python3-matplotlib python3-requests` zurück.

Es genügt also:

```bash
cd ~
git clone https://github.com/<user>/wetter-app
cd wetter-app
python3 main.py            # erste Debian-Pakete ggf. per eigenes sudo-Passwort bestätigen
```

Manuelle Installation (wenn du die Automatik nicht magst):

```bash
sudo apt install -y python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

oder direkt per apt ohne venv:

```bash
sudo apt install -y python3-pyside6 python3-matplotlib python3-requests
```

## Vollbild

- **Permanent**: `python main.py --fullscreen` bzw. im Einstellungsdialog
  „Vollbild beim Start" aktivieren (wird in `config.json` gespeichert)
- **Fenstermodus erzwingen**: `python main.py --windowed`
- **Während des Laufs umschalten**: Taste **F11** oder **Esc**

Fenstermodus am Ende beachten: `config.json` → `"fullscreen": true` zeigt die
App direkt im Vollbild auf dem TV — oder der systemd-Dienst wird mit
`/home/pi/wetter-app/.venv/bin/python /home/pi/wetter-app/main.py --fullscreen`
gestartet.

## Autostart (per systemd — Start beim Boot, Neustart nach Fehler)

Autologin für den Desktop-Benutzer aktivieren
(`sudo raspi-config` → System Options → Boot/Auto Login → Desktop Autologin),
dann:

```bash
sudo tee /etc/systemd/system/wetter-app.service << 'EOF'
[Unit]
Description=Wetter-App (Open-Meteo)
After=graphical.target
Wants=graphical.target

[Service]
User=pi
Environment=DISPLAY=:0
WorkingDirectory=/home/pi/wetter-app
ExecStart=/home/pi/wetter-app/.venv/bin/python /home/pi/wetter-app/main.py
Restart=always
RestartSec=15

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now wetter-app.service
```

Benutzername (hier `pi`) und Pfade anpassen. Für Wayland (Bookworm Standard)
statt `Environment=DISPLAY=:0` ggf.
`Environment=WAYLAND_DISPLAY=wayland-0` und `Environment=XDG_SESSION_TYPE=wayland`
setzen — erstere Variante funktioniert auf Bildschirm-KWS mit X meist direkt.
Praxistest: `journalctl -u wetter-app -f`.

## Konfigurationsdatei

`config.json` entsteht beim ersten Speichern neben dem Programm. Manueller
Vorab-Beispiel:

```json
{
  "location": { "name": "Berlin", "latitude": 52.52, "longitude": 13.41, "timezone": "auto" },
  "refresh_minutes": 30,
  "forecast_days": 16,
  "hourly_hours": 24,
  "units": { "temperature": "celsius", "wind": "kmh" },
  "blocks": { "current": true, "hourly_chart": true, "daily_overview": true, "extras": true },
  "fullscreen": true
}
```

## Ordnerstruktur

```text
wetter-app/
  main.py              Entry + Hauptfenster, Threads, Theme, Vollbild-Optionen
  bootstrap.py        installiert fehlende Pakete selbst (pip -> apt-Fallback)
  api.py               Open-Meteo Forecast + Geocoding, Zeit-Slicing
  widgets.py           Aktuell-Karte, 16-Tage-Tabelle, Details-Karte
  charts.py            Matplotlib-Stunden-Chart
  settings_dialog.py   Einstellungsdialog
  weathercodes.py      WMO-Codes -> deutsche Texte + Icons
  config.py            Laden/Speichern der Einstellungen
  requirements.txt
```

## Hinweise

- Open-Meteo aktualisiert die Wettermodelle je nach Modell alle ~15-60
  Minuten; ein Abrufintervall unter 15 Minuten bringt daher nichts und
  belastet den freien Dienst unnötig. Fair bleiben.
- Die App ist bewusst ohne Web-Stack (Flask, Grafana, Browser) gebaut:
  alles läuft in einem Python-Prozess, keine Server-Infrastruktur nötig.
