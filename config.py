# Einstellungen: config.json im Programmordner. Beim ersten Start wird eine
# Vorgabe angelegt. Alle Werte sind auch über den Einstellungsdialog änderbar.
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULTS = {
    "location": {
        "name": "Berlin",
        "latitude": 52.52,
        "longitude": 13.41,
        "timezone": "auto",
    },
    # Minuten zwischen zwei API-Abrufen. Open-Meteo aktualisiert die Modelle
    # i.d.R. alle 15-60 Minuten; schneller bringt nichts.
    "refresh_minutes": 30,
    "forecast_days": 16,          # 1-16, wirft UI-Panel unabhängig von der Abrufmenge
    "hourly_hours": 24,           # Stunden, die das Stunden-Chart zeigt
    "units": {"temperature": "celsius", "wind": "kmh"},
    "icons": {                    # Stil der Wetter-Symbole
        "style": "drawn",          # drawn (gezeichnet) | emoji (Font nötig)
        "size": "mittel",           # klein | mittel | groß
    },
    "blocks": {                   # welche Inhaltsblöcke sichtbar sind
        "current": True,
        "hourly_chart": True,
        "daily_overview": True,
        "extras": True,
    },
    # Fenster-Verhalten: fullscreen=True ideal für den TV/Monitor am Pi,
    # per Taste F11 bzw. Esc umschaltbar.
    "fullscreen": True,
}


def load():
    cfg = json.loads(json.dumps(DEFAULTS))  # deep copy
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user = json.load(f)
            _merge(cfg, user)
        except (OSError, ValueError) as e:
            print(f"Konnte config.json nicht laden ({e}) — nutze Vorgaben.")
    return cfg


def save(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"Konnte config.json nicht speichern: {e}")


def _merge(base, user):
    for key, val in user.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _merge(base[key], val)
        else:
            base[key] = val
