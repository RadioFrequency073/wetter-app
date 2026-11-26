"""Wiederverwendbare UI-Karten: Aktuell-Wetter, Tagesübersicht, Extras.

Alle Wettersymbole werden live als Vektorgrafik gezeichnet
(siehe weathericons.py) und sind daher auf jedem System sichtbar — auch ohne
installierten Emoji-Font. Über die Einstellungen lässt sich zurück auf Emojis
schalten ("icons.style").
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QWidget,
)

import weathercodes as wc
import weathericons as icons

# Anzeigetexte der Einheiten (Werte kommen aus api durch die Unit-Parameter)
TEMP_UNITS = {"celsius": "°C", "fahrenheit": "°F"}
WIND_UNITS = {"kmh": "km/h", "ms": "m/s", "mph": "mph", "kn": "kn"}
ICON_SIZES = {"klein": 72, "mittel": 96, "groß": 124}


def temp_unit(cfg):
    return TEMP_UNITS.get(cfg.get("units", {}).get("temperature", "celsius"), "°C")


def wind_unit(cfg):
    return WIND_UNITS.get(cfg.get("units", {}).get("wind", "kmh"), "km/h")


def icon_style(cfg):
    return cfg.get("icons", {}).get("style", "drawn")


class Card(QFrame):
    """Runder, dunkler Container — Basis aller Inhaltsblöcke
    (Styling im STYLESHEET von main.py, Klasse 'Card')."""

    def __init__(self, title=None):
        super().__init__()
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(18, 14, 18, 14)
        self.layout_.setSpacing(8)
        if title:
            t = QLabel(title)
            t.setStyleSheet("color: #8fa1b8; font-size: 13px; letter-spacing: 1px;")
            self.layout_.addWidget(t)


def icon_title(text, kind):
    """Detailüberschrift mit gezeichnetem Begleitsymbol."""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(6)
    ic = QLabel()
    ic.setPixmap(icons.ui_pixmap(kind, 16))
    t = QLabel(text)
    t.setStyleSheet("color: #8fa1b8; font-size: 12px;")
    h.addWidget(ic)
    h.addWidget(t)
    h.addStretch(1)
    return w


def _big(value, unit, color="#e8edf2"):
    lbl = QLabel(f"{value}{unit}")
    lbl.setStyleSheet(f"font-size: 30px; font-weight: 600; color: {color};")
    return lbl


class CurrentCard(Card):
    """Große Aktuell-Karte: gezeichnetes Wettersymbol, Temperatur, Details."""

    def __init__(self, title="Aktuell"):
        super().__init__(title)
        row = QHBoxLayout()
        row.setSpacing(18)

        self.icon = QLabel("–")
        self.icon.setStyleSheet("font-size: 84px;")
        self.icon.setFixedSize(130, 130)
        self.icon.setAlignment(Qt.AlignCenter)
        row.addWidget(self.icon)

        col = QVBoxLayout()
        col.setSpacing(2)
        self.place_label = QLabel("–")
        self.place_label.setStyleSheet("color: #8fa1b8; font-size: 14px;")
        self.temp_label = QLabel("–")
        self.temp_label.setStyleSheet("font-size: 62px; font-weight: 700;")
        self.desc_label = QLabel("–")
        self.desc_label.setStyleSheet("font-size: 22px;")
        col.addWidget(self.place_label)
        col.addWidget(self.temp_label)
        col.addWidget(self.desc_label)
        row.addLayout(col)
        row.addStretch(1)

        detail = QGridLayout()
        detail.setHorizontalSpacing(22)
        detail.setVerticalSpacing(4)
        self.details = {}
        for i, (key, label, icon_kind) in enumerate([
            ("feels", "Gefühlt", "feels"), ("humidity", "Feuchte", "humidity"),
            ("wind", "Wind", "wind"), ("precip", "Niederschlag", "precip"),
        ]):
            title_w = icon_title(label, icon_kind)
            val = QLabel("–")
            val.setStyleSheet("font-size: 20px; font-weight: 600;")
            detail.addWidget(title_w, 0, i, Qt.AlignLeft)
            detail.addWidget(val, 1, i)
            self.details[key] = val
        row.addLayout(detail)
        self.layout_.addLayout(row)
        self.layout_.addStretch(1)

    def update_data(self, cur, cfg=None):
        cfg = cfg or {}
        code = cur.get("weather_code", 0)
        is_day = cur.get("is_day", 1) == 1
        desc = wc.describe(code, is_day)[0]
        style = icon_style(cfg)
        if style == "emoji":
            self.icon.setPixmap(QPixmap())
            self.icon.setText(wc.describe(code, is_day)[1])
        else:
            size = ICON_SIZES.get(cfg.get("icons", {}).get("size", "mittel"), 96)
            self.icon.setText("")
            self.icon.setPixmap(icons.weather_pixmap(code, night=not is_day, size=size))
        self.desc_label.setText(desc)
        self.place_label.setText(cfg.get("location", {}).get("name", "–"))
        self.temp_label.setText(f"{round(cur.get('temperature_2m') or 0)}°")

        tu = temp_unit(cfg)
        self.details["feels"].setText(f"{round(cur.get('apparent_temperature') or 0)}{tu}")
        self.details["humidity"].setText(f"{cur.get('relative_humidity_2m', 0)} %")
        wind = cur.get("wind_speed_10m") or 0
        gust = cur.get("wind_gusts_10m")
        dir_txt = wc.wind_direction(cur.get("wind_direction_10m"))
        gust_txt = f" (Böen {round(gust)})" if gust else ""
        self.details["wind"].setText(f"{round(wind)} {wind_unit(cfg)} {dir_txt}{gust_txt}")
        precip = cur.get("precipitation") or 0
        self.details["precip"].setText(f"{precip:.1f} mm")


class DailyOverview(Card):
    """Tagesübersicht als Tabelle mit gezeichnetem Symbol, Min/Max, Regen,
    Regenwahrscheinlichkeit, Wind, UV."""

    HEADERS = ["", "Tag", "T max", "T min", "Regen", "Wahrsch.", "Wind", "UV"]

    def __init__(self, title="16-Tage-Vorschau"):
        super().__init__(title)
        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 44)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.layout_.addWidget(self.table)

    def update_data(self, daily, max_days, cfg=None):
        cfg = cfg or {}
        from datetime import datetime
        self.table.setRowCount(0)
        codes = daily.get("weather_code", [])
        size = min(len(codes), int(max_days) if max_days else 16)
        weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        tu = temp_unit(cfg)
        wu = wind_unit(cfg)
        style = icon_style(cfg)
        for i in range(size):
            row = self.table.rowCount()
            self.table.insertRow(row)
            date = datetime.fromisoformat(daily["time"][i])
            is_today = i == 0
            label = ("Heute" if is_today else f"{weekdays[date.weekday()]} {date.day:02d}.{date.month:02d}.")
            desc, emoji = wc.describe(codes[i])
            vals = [
                "",
                label,
                f"{round(daily['temperature_2m_max'][i])}{tu}",
                f"{round(daily['temperature_2m_min'][i])}{tu}",
                f"{daily.get('precipitation_sum', [0]*len(codes))[i]:.1f} mm",
                f"{daily.get('precipitation_probability_max', ['–']*len(codes))[i]} %",
                f"{round(daily.get('wind_speed_10m_max', [0]*len(codes))[i])} {wu}",
                f"{daily.get('uv_index_max', ['–']*len(codes))[i]}",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val) if col else "")
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                self.table.setItem(row, col, item)
                if is_today:
                    f = item.font(); f.setBold(True); item.setFont(f)
            sym = QTableWidgetItem()
            if style == "emoji":
                sym.setText(emoji)
            else:
                sym.setIcon(icons.weather_icon(codes[i], night=False, size=28))
            sym.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
            self.table.setItem(row, 0, sym)
            self.table.setRowHeight(row, 36)


class ExtrasCard(Card):
    """Karte mit Zusatzwerten: UV, Luftdruck, Sonnenauf-/untergang, Böen."""

    def __init__(self, title="Details"):
        super().__init__(title)
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(6)
        self.values = {}
        entries = [
            ("uv_max", "UV max heute", "uv"), ("uv_now", "UV jetzt", "uv"),
            ("pressure", "Luftdruck", "gauge"), ("astro", "Sonne", "astro"),
            ("humidity", "Feuchte", "humidity"), ("gusts", "Böen", "gusts"),
        ]
        for i, (key, label, icon_kind) in enumerate(entries):
            title_w = icon_title(label, icon_kind)
            v = QLabel("–")
            v.setStyleSheet("font-size: 19px; font-weight: 600;")
            v.setWordWrap(True)
            grid.addWidget(title_w, (i // 3) * 2, i % 3)
            grid.addWidget(v, (i // 3) * 2 + 1, i % 3)
            self.values[key] = v
        grid.setRowStretch(4, 1)
        self.layout_.addLayout(grid)
        self.layout_.addStretch(1)

    def update_data(self, cur, hourly, daily, utc_offset_seconds=None):
        uv_now = "–"
        uv_series = hourly.get("uv_index")
        if uv_series:
            from datetime import datetime, timedelta, timezone
            times = [datetime.fromisoformat(t) for t in hourly["time"]]
            if utc_offset_seconds is not None:
                now = (datetime.now(timezone.utc)
                       + timedelta(seconds=utc_offset_seconds)).replace(tzinfo=None)
            else:
                now = datetime.now().astimezone().replace(tzinfo=None)
            idx = min(
                range(len(times)),
                key=lambda i: abs((times[i] - now).total_seconds()),
            )
            uv_now = f"{uv_series[idx]:.1f} ({wc.comfort_uv(uv_series[idx])})"

        uv_max = daily.get("uv_index_max", [None])
        uv_max = uv_max[0] if uv_max else None
        self.values["uv_now"].setText(str(uv_now))
        self.values["uv_max"].setText(
            f"{uv_max} ({wc.comfort_uv(uv_max)})" if uv_max is not None else "–"
        )

        pressure = cur.get("surface_pressure")
        self.values["pressure"].setText(
            f"{round(pressure)} hPa" if pressure else "–"
        )

        sunrise = (daily.get("sunrise", [""])[0] or "")[11:16]
        sunset = (daily.get("sunset", [""])[0] or "")[11:16]
        self.values["astro"].setText(f"↑ {sunrise}  ↓ {sunset}" if sunrise else "–")

        self.values["humidity"].setText(f"{cur.get('relative_humidity_2m', 0)} %")
        gusts = cur.get("wind_gusts_10m")
        self.values["gusts"].setText(f"{round(gusts)} km/h" if gusts else "–")
