"""Live-Test gegen die echte Open-Meteo-API (Geocoding + Forecast) und
Verarbeitung der Antwort durch alle UI-Karten.

Läuft als eigener CI-Job mit continue-on-error: Der freie Dienst ist nicht
verfügbarkeitsgarantiert — ein Ausfall soll den Merge nicht blockieren,
aber sichtbar sein.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

import api
import widgets as w
from charts import HourlyChart

WMO_MIN, WMO_MAX = 0, 99

places = api.search_locations("München")
assert places, "Geocoding lieferte keine Treffer"
p = places[0]
assert isinstance(p["latitude"], (int, float)) and isinstance(p["longitude"], (int, float))
print("Ortssuche:", p["label"])

data = api.fetch_forecast(p["latitude"], p["longitude"], forecast_days=16)
cur = data["current"]
for key in ("temperature_2m", "apparent_temperature", "relative_humidity_2m",
            "weather_code", "wind_speed_10m", "precipitation", "is_day"):
    assert key in cur, f"current.{key} fehlt"
assert WMO_MIN <= cur["weather_code"] <= WMO_MAX, "WMO-Code außerhalb des Bereichs"
assert len(data["hourly"]["time"]) >= 24, "zu wenige Stundenstempel"
assert len(data["daily"]["time"]) == 16, "16 Tageswerte erwartet"
assert data["daily"]["sunrise"] and data["daily"]["sunset"], "Sonnenzeiten fehlen"
print(f"Aktuell: {cur['temperature_2m']} °C, Code {cur['weather_code']}, "
      f"{len(data['hourly']['time'])} h, {len(data['daily']['time'])} Tage")

cfg = {"location": p, "units": {"temperature": "celsius", "wind": "kmh"},
       "icons": {"style": "drawn", "size": "mittel"}}

card = w.CurrentCard()
card.update_data(cur, cfg)
assert card.place_label.text() == p["name"]
assert not card.icon.pixmap().isNull(), "Haupt-Wettersymbol fehlt"

table = w.DailyOverview()
table.update_data(data["daily"], 16, cfg)
assert table.table.rowCount() == 16
assert not table.table.item(0, 0).icon().isNull(), "Tabellen-Symbol fehlt"

extras = w.ExtrasCard()
extras.update_data(cur, data["hourly"], data["daily"], data["utc_offset_seconds"])

labels, series = api.next_hours(data["hourly"], 24, data["utc_offset_seconds"])
assert len(labels) == 24, "next_hours liefert nicht 24 Stunden"
chart = HourlyChart()
chart.update_data(labels, series, "°C")

print("API-Live-Test ok: Abruf + vollständige UI-Verarbeitung")
