"""Wieder verwendbare UI-Karten: Aktuell-Wetter, 16-Tage-Übersicht, Extras."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy,
)

import weathercodes as wc


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


def _big(value, unit, color="#e8edf2"):
    lbl = QLabel(f"{value}{unit}")
    lbl.setStyleSheet(f"font-size: 30px; font-weight: 600; color: {color};")
    return lbl


class CurrentCard(Card):
    """Große Aktuell-Karte links oben."""

    def __init__(self, title="Aktuell"):
        super().__init__(title)
        row = QHBoxLayout()
        row.setSpacing(18)

        self.icon = QLabel("❓")
        self.icon.setStyleSheet("font-size: 84px;")
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
        for i, (key, label) in enumerate([
            ("feels", "Gefühlt"), ("humidity", "Feuchte"),
            ("wind", "Wind"), ("precip", "Niederschlag"),
        ]):
            title = QLabel(label)
            title.setStyleSheet("color: #8fa1b8; font-size: 12px;")
            val = QLabel("–")
            val.setStyleSheet("font-size: 20px; font-weight: 600;")
            detail.addWidget(title, 0, i)
            detail.addWidget(val, 1, i)
            self.details[key] = val
        row.addLayout(detail)
        self.layout_.addLayout(row)
        self.layout_.addStretch(1)

    def update_data(self, cur, timezone_name=""):
        code = cur.get("weather_code", 0)
        is_day = cur.get("is_day", 1) == 1
        desc, emoji = wc.describe(code, is_day)
        self.icon.setText(emoji)
        self.desc_label.setText(desc)
        self.temp_label.setText(f"{round(cur.get('temperature_2m') or 0)}°")

        self.details["feels"].setText(f"{cur.get('apparent_temperature', 0)}°")
        self.details["humidity"].setText(f"{cur.get('relative_humidity_2m', 0)} %")
        wind = cur.get("wind_speed_10m") or 0
        gust = cur.get("wind_gusts_10m")
        dir_txt = wc.wind_direction(cur.get("wind_direction_10m"))
        gust_txt = f" (Böen {round(gust)})" if gust else ""
        self.details["wind"].setText(f"{round(wind)} km/h {dir_txt}{gust_txt}")
        precip = cur.get("precipitation") or 0
        self.details["precip"].setText(f"{precip:.1f} mm")


class DailyOverview(Card):
    """16-Tage-Übersicht als Tabelle mit Emoji, Min/Max, Regen, Wind, UV."""

    HEADERS = ["", "Tag", "T max", "T min", "Regen", "Wahrsch.", "Wind", "UV"]

    def __init__(self, title="16-Tage-Vorschau"):
        super().__init__(title)
        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Horizontale Kopfzeile hübsch halten, Spalten füllen den Platz
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.layout_.addWidget(self.table)

    def update_data(self, daily, max_days):
        from datetime import datetime
        self.table.setRowCount(0)
        codes = daily.get("weather_code", [])
        size = min(len(codes), int(max_days) if max_days else 16)
        weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        for i in range(size):
            row = self.table.rowCount()
            self.table.insertRow(row)
            date = datetime.fromisoformat(daily["time"][i])
            is_today = i == 0
            label = ("Heute" if is_today else f"{weekdays[date.weekday()]} {date.day:02d}.{date.month:02d}.")
            _, emoji = wc.describe(codes[i])
            vals = [
                emoji,
                label,
                f"{round(daily['temperature_2m_max'][i])}°C",
                f"{round(daily['temperature_2m_min'][i])}°C",
                f"{daily.get('precipitation_sum', [0]*len(codes))[i]:.1f} mm",
                f"{daily.get('precipitation_probability_max', ['–']*len(codes))[i]} %",
                f"{round(daily.get('wind_speed_10m_max', [0]*len(codes))[i])} km/h",
                f"{daily.get('uv_index_max', ['–']*len(codes))[i]}",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                self.table.setItem(row, col, item)
                if is_today:
                    from PySide6.QtGui import QFont
                    f = item.font(); f.setBold(True); item.setFont(f)
            # Emojis in der ersten Spalte größer darstellen
            self.table.setRowHeight(row, 34)


class ExtrasCard(Card):
    """Karte mit Zusatzwerten: UV, Luftdruck, Sonnenauf-/untergang,
    stündlicher UV-Ausblick für heute."""

    def __init__(self, title="Details"):
        super().__init__(title)
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(6)
        self.values = {}
        entries = [
            ("uv_max", "UV max heute"), ("uv_now", "UV jetzt"),
            ("pressure", "Luftdruck"), ("astro", "Sonne"),
            ("humidity", "Feuchte"), ("gusts", "Böen"),
        ]
        for i, (key, label) in enumerate(entries):
            t = QLabel(label)
            t.setStyleSheet("color: #8fa1b8; font-size: 12px;")
            v = QLabel("–")
            v.setStyleSheet("font-size: 19px; font-weight: 600;")
            v.setWordWrap(True)
            grid.addWidget(t, (i // 3) * 2, i % 3)
            grid.addWidget(v, (i // 3) * 2 + 1, i % 3)
            self.values[key] = v
        grid.setRowStretch(4, 1)
        self.layout_.addLayout(grid)
        self.layout_.addStretch(1)

    def update_data(self, cur, hourly, daily, utc_offset_seconds=None):
        uv_now = "–"
        # stündlicher UV-Index: zum aktuellen Zeitpunkt greifen so gut es geht
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
