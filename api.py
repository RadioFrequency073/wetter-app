# Open-Meteo API-Layer: Forecast + Geocoding, mit Timeout, Retry und Fehlerklassen.
import requests
from datetime import datetime, timedelta, timezone

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Welche Felder wir von der API holen. Der UI-Layer entscheidet darüber,
# welche Blöcke er daraus anzeigt.
CURRENT_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "is_day",
    "weather_code",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
    "surface_pressure",
    "precipitation",
]

HOURLY_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "uv_index",
    "relative_humidity_2m",
]

DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "uv_index_max",
    "sunrise",
    "sunset",
]


class ApiError(Exception):
    """Fehler beim Abruf der Wetterdaten (Netzwerk, Server, Parsen)."""


def search_locations(query, count=8):
    """Stadtname -> Liste von Treffern über die Open-Meteo Geocoding API.

    Jeder Treffer ist ein dict mit: name, country, admin1 (Bundesland),
    latitude, longitude, timezone.
    """
    if not query or len(query.strip()) < 2:
        return []
    try:
        r = requests.get(
            GEOCODE_URL,
            params={"name": query.strip(), "count": count, "language": "de", "format": "json"},
            timeout=10,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
    except (requests.RequestException, ValueError) as e:
        raise ApiError(f"Ortssuche fehlgeschlagen: {e}") from e

    places = []
    for item in results:
        parts = [item.get("name")]
        if item.get("admin1") and item["admin1"] != item.get("name"):
            parts.append(item["admin1"])
        if item.get("country"):
            parts.append(item["country"])
        places.append(
            {
                "label": ", ".join(p for p in parts if p),
                "name": item.get("name", "?"),
                "latitude": item["latitude"],
                "longitude": item["longitude"],
                "timezone": item.get("timezone", "auto"),
            }
        )
    return places


def fetch_forecast(latitude, longitude, forecast_days=16, temperature_unit="celsius", wind_speed_unit="kmh"):
    """Hole Forecast-Daten für Koordinaten. Liefert ein dict zurück, das alle
    UI-Blöcke bedient: current, hourly (Zeitreihe) und daily (Tagesübersicht).

    'timezone=auto' sorgt dafür, dass die Zeitstempel in Lokalzeit des Ortes
    kommen — wichtig, damit 'nächste 24 Stunden' am Ort selbst ausgerichtet ist.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "temperature_unit": temperature_unit,
        "wind_speed_unit": wind_speed_unit,

        "current": ",".join(CURRENT_FIELDS),
        "hourly": ",".join(HOURLY_FIELDS),
        "daily": ",".join(DAILY_FIELDS),
        "forecast_days": max(1, min(16, int(forecast_days))),
        "timezone": "auto",
    }
    last_error = None
    for attempt in range(3):
        try:
            r = requests.get(FORECAST_URL, params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            last_error = e
    raise ApiError(f"Weatherdaten konnten nicht geladen werden: {last_error}") from last_error


def next_hours(hourly, hours=24, utc_offset_seconds=None):
    """Schneide aus der stündlichen Zeitreihe die nächsten `hours` Stunden ab
    der vollen aktuellen Stunde heraus. Liefert (labels, series-dict).

    Open-Meteo liefert mit timezone=auto naive Zeitstempel in Ortszeit des
    Ortes. Damit 'jetzt' denselben Referenzrahmen hat, rechnet die App die
    UTC-Zeit mit utc_offset_seconds aus der API-Antwort in Ortszeit um.
    """
    times = [datetime.fromisoformat(t) for t in hourly["time"]]
    if utc_offset_seconds is not None:
        now = (datetime.now(timezone.utc) + timedelta(seconds=utc_offset_seconds)
               ).replace(tzinfo=None)
    else:
        now = datetime.now().astimezone().replace(tzinfo=None)
    # Index der aktuellen Stunde: erster Zeitstempel im Zeitfenster [now - 1h, now)
    start = 0
    for i, t in enumerate(times):
        if t <= now < t + timedelta(hours=1):
            start = i
            break
    else:
        start = 0
    end = min(start + hours, len(times))
    labels = [times[i].strftime("%H:%M") for i in range(start, end)]
    series = {k: hourly[k][start:end] for k in HOURLY_FIELDS if k in hourly}
    return labels, series


def parse_iso_list(values):
    """'2025-01-02T07:12' / '2025-01-02' -> datetime-Liste (Zeitzone aus API
    offset ist bei daily ohne Uhrzeit irrelevant; herein kommen Strings)."""
    out = []
    for v in values:
        out.append(datetime.fromisoformat(v) if v else None)
    return out


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()
