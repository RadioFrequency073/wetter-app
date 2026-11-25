"""Stunden-Chart (nächste 24 h): Temperatur-Linie + Regensummen-Balken,
gerendert mit Matplotlib und in PySide6 eingebettet (kein X-Server nötig)."""
import matplotlib
matplotlib.use("QtAgg")
matplotlib.rcParams["font.family"] = "DejaVu Sans"

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6.QtWidgets import QSizePolicy

from widgets import Card

BG = "#171e29"
FG = "#e8edf2"
GRID = "#2c3849"
BLUE = "#4da3ff"
TEAL = "#37c8ab"


class HourlyChart(Card):
    def __init__(self, title="Nächste 24 Stunden"):
        super().__init__(title)
        self.fig = Figure(figsize=(6, 3), dpi=100, facecolor=BG)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumHeight(220)
        self.layout_.addWidget(self.canvas, 1)

    def update_data(self, labels, series):
        self.fig.clear()
        temps = series.get("temperature_2m", [])
        precip = series.get("precipitation", [])
        prob = series.get("precipitation_probability", [])
        if not temps:
            return

        ax = self.fig.add_subplot(111)
        ax.set_facecolor(BG)

        # Regensummen als Balken (eigene Achse, damit Temperaturen skaliert
        # unabhängig bleiben)
        ax2 = ax.twinx()
        if precip:
            colors = [TEAL if p > 0 else GRID for p in precip]
            ax2.bar(range(len(labels)), precip, color=colors, alpha=0.55, width=0.7)
            if any(p > 0 for p in precip):
                ymax = max(precip) * 1.6
            else:
                ymax = 1
            ax2.set_ylim(0, max(ymax, 1))
            ax2.set_ylabel("mm", color=TEAL, fontsize=9)
            ax2.tick_params(axis="y", colors=TEAL, labelsize=8)

        # Temperatur-Linie + Beschriftung jeden Punkts
        ax.plot(range(len(temps)), temps, color=BLUE, linewidth=2.2,
                marker="o", markersize=3.5)
        ax.set_ylabel("°C", color=BLUE, fontsize=9)
        ax.tick_params(axis="y", colors=BLUE, labelsize=8)
        ymin, ymax = min(temps), max(temps)
        pad = max((ymax - ymin) * 0.25, 1.5)
        ax.set_ylim(ymin - pad, ymax + pad)

        step = max(1, len(labels) // 8)   # nicht jedes Label zeigen
        ax.set_xticks(range(0, len(labels), step))
        ax.set_xticklabels(labels[::step], color=FG, fontsize=8)
        for spine in list(ax.spines.values()) + list(ax2.spines.values()):
            spine.set_visible(False)
        ax.grid(axis="y", color=GRID, linewidth=0.5, alpha=0.5)
        ax.tick_params(axis="y", length=0)
        ax2.tick_params(axis="y", length=0)

        # Regenwahrscheinlichkeit ans Diagramm-Füßchen
        if prob:
            max_prob = max(p or 0 for p in prob)
            note = f"Regenwahrscheinlichkeit (max): {max_prob} %"
            self.fig.text(0.99, 0.02, note, ha="right", fontsize=8, color="#8fa1b8")

        self.fig.tight_layout()
        self.canvas.draw_idle()
