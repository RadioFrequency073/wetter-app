"""Einstellungsdialog: Ort, Aktualisierungsintervall, Tage/Stunden,
Einheiten, Symbolstil/-größe, Sichtbarkeit der Inhaltsblöcke und Vollbild."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QSpinBox, QCheckBox,
    QComboBox, QDialogButtonBox, QLabel, QGroupBox,
)

import widgets


def _combo(options, current):
    """ComboBox mit (key, anzeigetext)-Paaren, vorausgewählt auf `current`."""
    cb = QComboBox()
    for key, label in options:
        cb.addItem(label, key)
        if key == current:
            cb.setCurrentIndex(cb.count() - 1)
    return cb


class SettingsDialog(QDialog):
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.setMinimumWidth(460)
        self.cfg_snapshot = {
            "location": dict(cfg["location"]),
            "refresh_minutes": int(cfg["refresh_minutes"]),
            "forecast_days": int(cfg["forecast_days"]),
            "hourly_hours": int(cfg["hourly_hours"]),
            "units": dict(cfg["units"]),
            "icons": dict(cfg.get("icons", {})),
            "blocks": dict(cfg["blocks"]),
            "fullscreen": bool(cfg.get("fullscreen", True)),
        }

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        # --- Ort ---
        loc = self.cfg_snapshot["location"]
        self.name_label = QLabel(f"{loc['name']}  ({loc['latitude']:.2f}, {loc['longitude']:.2f})")
        self.name_label.setStyleSheet("color: #8fa1b8;")
        form.addRow(QLabel("Ort (ändern: Suchfeld im Hauptfenster):"), self.name_label)

        # --- Abruf ---
        self.minutes = QSpinBox()
        self.minutes.setRange(5, 360)
        self.minutes.setSuffix(" Min")
        self.minutes.setValue(int(cfg["refresh_minutes"]))
        form.addRow(QLabel("Aktualisierung alle:"), self.minutes)

        self.days = QSpinBox()
        self.days.setRange(1, 16)
        self.days.setSuffix(" Tage")
        self.days.setValue(int(cfg["forecast_days"]))
        form.addRow(QLabel("Tage in der Übersicht:"), self.days)

        self.hours = QSpinBox()
        self.hours.setRange(6, 48)
        self.hours.setSuffix(" h")
        self.hours.setValue(int(cfg["hourly_hours"]))
        form.addRow(QLabel("Stunden im Chart:"), self.hours)

        # --- Einheiten ---
        self.units = _combo(
            [("celsius", "Celsius (°C)"), ("fahrenheit", "Fahrenheit (°F)")],
            cfg["units"].get("temperature", "celsius"),
        )
        form.addRow(QLabel("Temperatureinheit:"), self.units)

        self.wind_units = _combo(
            [("kmh", "Kilometer pro Stunde (km/h)"), ("ms", "Meter pro Sekunde (m/s)"),
             ("mph", "Meilen pro Stunde (mph)"), ("kn", "Knoten (kn)")],
            cfg["units"].get("wind", "kmh"),
        )
        form.addRow(QLabel("Windeinheit:"), self.wind_units)

        # --- Symbole ---
        self.icon_style = _combo(
            [("drawn", "Gezeichnete Symbole (immer sichtbar)"),
             ("emoji", "Emoji (benötigt Emoji-Font)")],
            cfg.get("icons", {}).get("style", "drawn"),
        )
        form.addRow(QLabel("Symbolstil:"), self.icon_style)

        self.icon_size = _combo(
            [("klein", "Klein"), ("mittel", "Mittel"), ("groß", "Groß")],
            cfg.get("icons", {}).get("size", "mittel"),
        )
        form.addRow(QLabel("Symbolgröße (Hauptanzeige):"), self.icon_size)

        root.addLayout(form)

        # --- Block-Sichtbarkeit ---
        blocks_box = QGroupBox("Angezeigte Blöcke")
        blocks_layout = QVBoxLayout(blocks_box)
        self.block_checks = {}
        labels = {
            "current": "Aktuell-Karte",
            "hourly_chart": "Stunden-Chart",
            "daily_overview": "Tagesübersicht",
            "extras": "Details (UV, Luftdruck, Sonne …)",
        }
        for key, label in labels.items():
            cb = QCheckBox(label)
            cb.setChecked(bool(cfg["blocks"].get(key, True)))
            blocks_layout.addWidget(cb)
            self.block_checks[key] = cb
        root.addWidget(blocks_box)

        # --- Anzeige ---
        self.fullscreen_cb = QCheckBox("Vollbild beim Start (TV/Monitor)")
        self.fullscreen_cb.setChecked(bool(cfg.get("fullscreen", True)))
        root.addWidget(self.fullscreen_cb)

        hint = QLabel("Tasten: F11 / Esc = Vollbild umschalten")
        hint.setStyleSheet("color: #8fa1b8; font-size: 12px;")
        root.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def result_config(self):
        cfg = dict(self.cfg_snapshot)
        cfg["refresh_minutes"] = self.minutes.value()
        cfg["forecast_days"] = self.days.value()
        cfg["hourly_hours"] = self.hours.value()
        cfg["units"]["temperature"] = self.units.currentData()
        cfg["units"]["wind"] = self.wind_units.currentData()
        cfg["icons"] = {
            "style": self.icon_style.currentData(),
            "size": self.icon_size.currentData(),
        }
        cfg["fullscreen"] = self.fullscreen_cb.isChecked()
        cfg["blocks"] = {k: cb.isChecked() for k, cb in self.block_checks.items()}
        return cfg
