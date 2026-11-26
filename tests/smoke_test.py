"""Headless-Smoke-Test für die CI: Qt-Offscreen, keine Netzwerkzugriffe.

Prüft: Alle gezeichneten Wetter- und UI-Symbole rendern, die Karten nehmen
Beispieldaten an und der Stunden-Chart zeichnet. Bewusst ohne `main`
(dort startet der Bootstrap und ein Netzwerkabruf).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

import weathericons as icons
import widgets as w
import api
from charts import HourlyChart

WMO_CODES = sorted(set(
    list(range(0, 4)) + [45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67,
                         71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99]
))

for code in WMO_CODES:
    for night in (False, True):
        pm = icons.weather_pixmap(code, night=night, size=96)
        assert not pm.isNull(), f"Wettersymbol {code} (night={night}) leer"
for kind in ("thermo", "droplet", "wind", "umbrella", "gauge", "sun",
             "sunrise", "sunset", "location", "uv", "humidity", "gusts",
             "precip", "feels", "place"):
    assert not icons.ui_pixmap(kind, 18).isNull(), f"UI-Symbol {kind} leer"

CUR = {
    "temperature_2m": 7.4, "apparent_temperature": 4.9,
    "relative_humidity_2m": 81, "is_day": 1, "weather_code": 61,
    "wind_speed_10m": 14.2, "wind_gusts_10m": 39.1, "wind_direction_10m": 245,
    "surface_pressure": 1016.3, "precipitation": 0.3,
}
HOURLY = {
    "time": ["2025-01-02T%02d:00" % h for h in range(24)],
    "temperature_2m": [5.0 + 0.2 * h for h in range(24)],
    "precipitation": [0.0] * 24,
    "precipitation_probability": [10, 20, 30, 40] * 6,
    "weather_code": [61] * 24, "wind_speed_10m": [10] * 24,
    "uv_index": [0.0] * 24, "relative_humidity_2m": [70] * 24,
    "apparent_temperature": [3.0] * 24,
}
DAILY = {
    "time": ["2025-01-02", "2025-01-03"], "weather_code": [61, 95],
    "temperature_2m_max": [8.1, 9.2], "temperature_2m_min": [2.3, 3.1],
    "apparent_temperature_max": [7.0, 8.0], "precipitation_sum": [1.2, 0.0],
    "precipitation_probability_max": [70, 90], "wind_speed_10m_max": [22, 31],
    "uv_index_max": [1.2, 1.0],
    "sunrise": ["2025-01-02T08:17", "2025-01-03T08:17"],
    "sunset": ["2025-01-02T16:34", "2025-01-03T16:35"],
}

CFG_DEFAULT = {
    "location": {"name": "Berlin", "latitude": 52.52, "longitude": 13.41},
    "units": {"temperature": "celsius", "wind": "kmh"},
    "icons": {"style": "drawn", "size": "mittel"},
}
CFG_ALT = {
    "location": {"name": "Berlin", "latitude": 52.52, "longitude": 13.41},
    "units": {"temperature": "fahrenheit", "wind": "mph"},
    "icons": {"style": "emoji", "size": "groß"},
}

card = w.CurrentCard()
card.update_data(CUR, CFG_DEFAULT)
assert card.place_label.text() == "Berlin"
assert not card.icon.pixmap().isNull(), "Haupt-Wettersymbol fehlt"
assert "°C" in card.details["feels"].text()
assert "km/h" in card.details["wind"].text()

table = w.DailyOverview()
table.update_data(DAILY, 16, CFG_DEFAULT)
assert table.table.rowCount() == 2
assert "°C" in table.table.item(0, 2).text()
assert not table.table.item(0, 0).icon().isNull(), "Tabellen-Symbol fehlt"

card.update_data(CUR, CFG_ALT)
assert "°F" in card.details["feels"].text()
assert "mph" in card.details["wind"].text()
assert card.icon.text() and card.icon.pixmap().isNull(), "Emoji-Fallback kaputt"

table.update_data(DAILY, 16, CFG_ALT)
assert "°F" in table.table.item(0, 2).text()
assert "mph" in table.table.item(0, 6).text()

extras = w.ExtrasCard()
extras.update_data(CUR, HOURLY, DAILY, 3600)

labels, series = api.next_hours(HOURLY, 24)
chart = HourlyChart()
chart.update_data(labels, series, "°C")
chart.update_data(labels, series, "°F")

print(f"Smoke-Test ok: {len(WMO_CODES)} WMO-Codes x Tag/Nacht, "
      f"15 UI-Symbole, Karten, Tabelle, Chart")
