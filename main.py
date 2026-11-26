"""Wetter-App für Raspberry Pi 4 — Open-Meteo, PySide6.

Start: python main.py
Beim ersten Aufruf installiert die App fehlende Python-Pakete selbstständig
(siehe bootstrap.py). Für die Vollbild-Anzeige auf Monitor/TV:
- permanent:  python main.py --fullscreen   (oder Option im Einstellungsdialog)
- als Fenster: python main.py --windowed
- umschalten während des Laufs: F11 oder Esc
"""

import sys

# Zuerst: Fehlende Pakete automatisch nachinstallieren (pip, Fallback apt).
# Muss vor dem allerersten PySide6-/matplotlib-Import passieren.
import bootstrap
bootstrap.ensure_packages()

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QScrollArea, QFrame,
)
import api
from api import ApiError
import weathercodes as wc
import config
from charts import HourlyChart
from settings_dialog import SettingsDialog
import widgets
import weathericons as icons
from widgets import CurrentCard, DailyOverview, ExtrasCard, Card

REFRESH = 60_000  # ms — UI-Takt für "Wann zuletzt aktualisiert"-Anzeige


class FetchWorker(QObject):
    """Lädt Forecast-Daten in einem Hintergrund-Thread, damit die GUI nicht
    einfriert, wenn das Netz langsam ist."""
    done = Signal(object)      # dict: API-Antwort
    failed = Signal(str)       # Fehlermeldung
    places_ready = Signal(list)  # Geocoding-Treffer

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg

    def fetch_forecast(self):
        loc = self.cfg["location"]
        try:
            data = api.fetch_forecast(
                loc["latitude"], loc["longitude"],
                forecast_days=max(self.cfg["forecast_days"], 2),
                temperature_unit=self.cfg["units"].get("temperature", "celsius"),
                wind_speed_unit=self.cfg["units"].get("wind", "kmh"),
            )
            self.done.emit(data)
        except ApiError as e:
            self.failed.emit(str(e))

    def search(self, query):
        try:
            self.places_ready.emit(api.search_locations(query))
        except ApiError as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = config.load()
        self.data = None
        self.setWindowTitle("Wetter — Open-Meteo")
        self.resize(1280, 800)

        self._build_ui()

        # Hintergrund-Worker in eigenem Thread
        self.worker = FetchWorker(self.cfg)
        self.thread = None
        self.worker.done.connect(self._on_data)
        self.worker.failed.connect(self._on_error)
        self.worker.places_ready.connect(self._on_places)

        # Abruf-Timer aus der Konfiguration
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(
            max(5, int(self.cfg["refresh_minutes"])) * 60_000
        )

        # "zuletzt aktualisiert"-Anzeige regelmäßig aktualisieren
        self.clock = QTimer(self)
        self.clock.timeout.connect(self._update_last_refresh_label)
        self.clock.start(REFRESH)

        self.refresh()

    # ---------- UI-Aufbau ----------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # Kopfzeile: Ortssuche + Einstellungen
        header = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Ort suchen (z. B. München, Hamburg, Wien)…")
        self.search_box.setFixedWidth(420)
        self.search_box.setFixedHeight(34)
        self.search_box.returnPressed.connect(self._do_search)
        # Vorschlagssuche mit 350 ms Debounce, damit nicht bei jedem Zeichen
        # ein API-Aufruf feuert.
        self.search_debounce = QTimer(self)
        self.search_debounce.setSingleShot(True)
        self.search_debounce.setInterval(350)
        self.search_debounce.timeout.connect(self._do_search)
        self.search_box.textEdited.connect(lambda _: self.search_debounce.start())

        self.place_combo = QComboBox()
        self.place_combo.setFixedHeight(34)
        self.place_combo.setMinimumWidth(320)
        self.place_combo.setVisible(False)
        self.place_combo.activated.connect(self._on_place_chosen)

        self.settings_btn = QPushButton("Einstellungen")
        self.settings_btn.setFixedHeight(34)
        self.settings_btn.clicked.connect(self.open_settings)

        pin = QLabel()
        pin.setPixmap(icons.ui_pixmap("place", 22))
        header.addWidget(pin, 0, Qt.AlignVCenter)
        header.addWidget(self.search_box)
        header.addWidget(self.place_combo)
        header.addStretch(1)
        self.updated_label = QLabel("")
        header.addWidget(self.updated_label)
        header.addWidget(self.settings_btn)
        root.addLayout(header)

        # Inhalt: Kartenraster in ScrollArea, damit es auch auf kleineren
        # TVs komplett lesbar bleibt.
        self.content = QWidget()
        self.content_grid = QGridLayout(self.content)
        self.content_grid.setSpacing(12)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll, 1)

        self.current_card = CurrentCard()
        self.hourly_chart = HourlyChart()
        self.daily_overview = DailyOverview()
        self.extras_card = ExtrasCard()

        self._relayout()

    def _relayout(self):
        """Blöcke anordnen: Aktuell + Stunden-Chart volle Breite,
        Übersicht und Details teilen sich die untere Reihe (wenn beide an)."""
        blocks = self.cfg["blocks"]

        # Alte Positionen entfernen, Widgets verstecken
        for w in (self.current_card, self.hourly_chart,
                  self.daily_overview, self.extras_card):
            self.content_grid.removeWidget(w)
            w.hide()

        grid = self.content_grid
        order = []
        if blocks.get("current", True):
            order.append(self.current_card)
        if blocks.get("hourly_chart", True):
            order.append(self.hourly_chart)
        bottom = []   # Karten, die sich unten eine Reihe teilen
        if blocks.get("daily_overview", True):
            bottom.append(self.daily_overview)
        if blocks.get("extras", True):
            bottom.append(self.extras_card)

        row = 0
        for w in order:
            w.show()
            grid.addWidget(w, row, 0, 1, 2)
            row += 1

        if len(bottom) == 2:
            for w in bottom:
                w.show()
            grid.addWidget(bottom[0], row, 0, 1, 1)
            grid.addWidget(bottom[1], row, 1, 1, 1)
        elif bottom:
            bottom[0].show()
            grid.addWidget(bottom[0], row, 0, 1, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

    # ---------- Datenfluss ----------

    def refresh(self):
        if self.thread is not None and self.thread.isRunning():
            return  # vorheriger Abruf läuft noch — nichts doppelt
        from PySide6.QtCore import QThread
        self.worker.cfg = self.cfg
        self.thread = QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.fetch_forecast)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(lambda: setattr(self, "thread", None))
        self.thread.start()

    def _on_data(self, data):
        if self.thread:
            self.thread.quit()
        self.data = data
        self.last_refresh = self._now()
        self.updated_label.setText(f"Stand: {self.last_refresh}")

        cur = data.get("current", {})
        hourly = data.get("hourly", {})
        daily = data.get("daily", {})

        if self.cfg["blocks"].get("current", True):
            self.current_card.update_data(cur, self.cfg)
        if self.cfg["blocks"].get("hourly_chart", True):
            labels, series = api.next_hours(hourly, int(self.cfg["hourly_hours"]))
            self.hourly_chart.update_data(
                labels, series, widgets.temp_unit(self.cfg)
            )
        if self.cfg["blocks"].get("daily_overview", True):
            self.daily_overview.update_data(
                daily, int(self.cfg["forecast_days"]), self.cfg
            )
        if self.cfg["blocks"].get("extras", True):
            self.extras_card.update_data(
                cur, hourly, daily, data.get("utc_offset_seconds")
            )

    def _on_error(self, message):
        self.updated_label.setText("Abruf fehlgeschlagen")
        # Bewusst kein blockierendes Dialogfeld bei laufender App: Der
        # nächste Timer-Abruf versucht es erneut.
        self.statusBar().showMessage(message, 10_000)

    def _update_last_refresh_label(self):
        if hasattr(self, "last_refresh") and self.data:
            self.updated_label.setText(f"Stand: {self.last_refresh}")

    def _now(self):
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    # ---------- Ortssuche ----------

    def _do_search(self):
        query = self.search_box.text().strip()
        if len(query) < 2:
            return
        from PySide6.QtCore import QThread
        self._search_thread = QThread(self)
        self.search_worker = FetchWorker(self.cfg)
        self.search_worker.places_ready.connect(self._on_places)
        self.search_worker.failed.connect(self._on_error)
        self.search_worker.moveToThread(self._search_thread)
        self._search_thread.started.connect(lambda: self.search_worker.search(query))
        self._search_thread.finished.connect(self._search_thread.deleteLater)
        self._search_thread.start()

    def _on_places(self, places):
        self.place_combo.blockSignals(True)
        self.place_combo.clear()
        for p in places:
            self.place_combo.addItem(p["label"], p)
        self.place_combo.setVisible(bool(places))
        self.place_combo.blockSignals(False)
        if places:
            self.place_combo.showPopup()

    def _on_place_chosen(self, index):
        place = self.place_combo.itemData(index)
        if not place:
            return
        self.cfg["location"] = place
        config.save(self.cfg)
        self.place_combo.setVisible(False)
        self.search_box.clear()
        self.place_combo.clear()
        self.refresh()

    # ---------- Einstellungen / Tasten ----------

    def open_settings(self):
        dlg = SettingsDialog(self, self.cfg)
        if dlg.exec():
            self.cfg = dlg.result_config()
            config.save(self.cfg)
            self.refresh_timer.setInterval(
                max(5, int(self.cfg["refresh_minutes"])) * 60_000
            )
            self._relayout()
            self.refresh()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F11 or event.key() == Qt.Key.Key_Escape:
            self._toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()


def main():
    # Vollbild-Option per Kommandozeile:
    #   python main.py --fullscreen  -> erzwingt Vollbild
    #   python main.py --windowed    -> erzwingt Fenster (überschreibt config.json)
    #   ohne Argument                -> Verhalten aus config.json ("fullscreen")
    force_fullscreen = "--fullscreen" in sys.argv
    force_windowed = "--windowed" in sys.argv

    app = QApplication(sys.argv)
    app.setApplicationName("Wetter")
    font = QFont()
    font.setPointSize(11)
    app.setFont(font)
    app.setStyleSheet(STYLESHEET)

    win = MainWindow()
    if force_fullscreen or (win.cfg.get("fullscreen", True) and not force_windowed):
        win.showFullScreen()
    else:
        win.show()
    sys.exit(app.exec())


STYLESHEET = """
QMainWindow { background: #10151c; }
QWidget { color: #e8edf2; font-family: 'Segoe UI', 'DejaVu Sans', sans-serif; }
QLabel { background: transparent; }
QLineEdit, QComboBox {
    background: #1b2330; border: 1px solid #2c3849; border-radius: 8px;
    padding: 4px 10px; color: #e8edf2;
}
QPushButton {
    background: #1b2330; border: 1px solid #2c3849; border-radius: 8px;
    padding: 6px 14px; color: #e8edf2;
}
QPushButton:hover { background: #243044; }
Card { background: #171e29; border-radius: 14px; }
QScrollArea { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #2c3849; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QTableWidget { background: transparent; border: none; }
QHeaderView::section { background: transparent; border: none; color: #8fa1b8; }
"""


if __name__ == "__main__":
    main()
