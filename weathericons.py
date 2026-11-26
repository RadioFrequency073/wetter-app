"""Gezeichnete Wetter- und UI-Symbole (QPainter) — ohne Bilddateien.

Hintergrund: Auf dem Raspberry Pi (schlankes Raspberry Pi OS ohne Emoji-Font)
werden Wetter-Emojis oft als leere Kaestchen dargestellt. Deshalb rendert die
App ihre Symbole selbst als Vektorgrafik: farbige Wettersymbole fuer die
Hauptanzeige (Tag-/Nacht-Variante) und kleine einfarbige Begleitsymbole fuer
die Detailbeschriftungen. Alles skaliert scharf auf jeden Monitor.
"""
from math import cos, pi, sin

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF,
)

# Kontraststarke Palette auf dunklem Grund
INK = "#8fa1b8"
SUN = "#ffcf5c"
MOON = "#ccd7ea"
CLOUD_LIGHT = "#c8d3e2"
CLOUD_DARK = "#8fa2ba"
RAIN = "#5aabff"
SNOW = "#eef4fc"
BOLT = "#ffd44d"
FOG = "#b9c6d6"

SCALE = 3  # interne Supersampling-Stufe -> immer scharf


def kind_for(code):
    """WMO-Wettercode -> Symbol-Kategorie fuer die gezeichneten Icons."""
    c = int(code or 0)
    if c == 0:
        return "clear"
    if c in (1, 2):
        return "partly"
    if c == 3:
        return "cloudy"
    if c in (45, 48):
        return "fog"
    if c in (51, 53, 56, 61, 80):
        return "drizzle"
    if c in (55, 57, 63, 66, 81):
        return "rain"
    if c in (65, 67, 82):
        return "heavyrain"
    if c in (71, 73, 77, 85):
        return "snow"
    if c in (75, 86):
        return "heavysnow"
    if c == 95:
        return "thunder"
    if c in (96, 99):
        return "thunderhail"
    return "cloudy"


def weather_pixmap(code, night=False, size=96):
    """Farbiges Wettersymbol fuer einen WMO-Code als QPixmap."""
    pm = QPixmap(size * SCALE, size * SCALE)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.scale(size * SCALE, size * SCALE)
    _weather(kind_for(code), night, p)
    p.end()
    pm.setDevicePixelRatio(SCALE)
    return pm


def weather_icon(code, night=False, size=96):
    return QIcon(weather_pixmap(code, night, size))


def ui_pixmap(kind, size=18, color=INK):
    """Kleines monochromes Begleitsymbol (Thermometer, Tropfen, Wind, ...)."""
    pm = QPixmap(size * SCALE, size * SCALE)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.scale(size * SCALE, size * SCALE)
    pen = QPen(QColor(color), 0.09)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(QColor(color))
    getattr(_UI, f"_{kind}", _UI._sun)(p)
    p.end()
    pm.setDevicePixelRatio(SCALE)
    return pm


def ui_icon(kind, size=18):
    return QIcon(ui_pixmap(kind, size))


# ---------- zeichnende Helfer (Koordinatenraum 0..1) ----------


def _pen(p, color, width, brush=Qt.NoBrush):
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(brush)


def _f(color, alpha=255):
    c = QColor(color)
    c.setAlpha(alpha)
    return QBrush(c)


def _sun_circle(p, cx, cy, r, with_rays=True):
    if with_rays:
        _pen(p, SUN, 0.045)
        for i in range(8):
            a = i * pi / 4
            p.drawLine(
                QPointF(cx + cos(a) * r * 1.35, cy + sin(a) * r * 1.35),
                QPointF(cx + cos(a) * r * 1.95, cy + sin(a) * r * 1.95),
            )
    _pen(p, SUN, 0.03, _f(SUN))
    p.drawEllipse(QPointF(cx, cy), r, r)


def _moon(p, cx, cy, r):
    _pen(p, MOON, 0.03, _f(MOON))
    p.drawEllipse(QPointF(cx, cy), r, r)
    p.setCompositionMode(QPainter.CompositionMode_Clear)
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(cx + r * 0.62, cy - r * 0.48), r * 0.88, r * 0.88)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)


def _cloud(p, cx=0.50, cy=0.52, w=0.66, color=CLOUD_LIGHT):
    h = w * 0.60
    x0, x1 = cx - w / 2, cx + w / 2
    yb = cy + h / 2
    r_left, r_top, r_right = w * 0.21, w * 0.30, w * 0.19
    path = QPainterPath()
    path.addEllipse(QPointF(x0 + w * 0.22, yb - r_left), r_left, r_left)
    path.addEllipse(QPointF(cx, yb - w * 0.44), r_top, r_top)
    path.addEllipse(QPointF(x1 - w * 0.18, yb - r_right), r_right, r_right)
    path.addRoundedRect(
        QRectF(x0 + w * 0.02, yb - w * 0.30, w * 0.96, w * 0.30), w * 0.15, w * 0.15
    )
    _pen(p, color, 0.02, _f(color))
    p.drawPath(path.simplified())
    return yb


def _rain_lines(p, n=3, heavy=False):
    width = 0.055 if heavy else 0.042
    _pen(p, RAIN, width)
    xs = [0.42, 0.52, 0.62] if n == 3 else [0.38, 0.48, 0.58, 0.68]
    for x in xs:
        p.drawLine(QPointF(x, 0.74), QPointF(x - 0.05, 0.92))


def _snow(p):
    _pen(p, SNOW, 0.035)
    for x, y in ((0.42, 0.80), (0.56, 0.86)):
        for a in (0, pi / 3, 2 * pi / 3):
            p.drawLine(
                QPointF(x - cos(a) * 0.055, y - sin(a) * 0.055),
                QPointF(x + cos(a) * 0.055, y + sin(a) * 0.055),
            )


def _bolt(p, extra_hail=False):
    pts = QPolygonF([
        QPointF(0.55, 0.66), QPointF(0.42, 0.86), QPointF(0.51, 0.86),
        QPointF(0.45, 1.06), QPointF(0.61, 0.80), QPointF(0.52, 0.80),
    ])
    _pen(p, BOLT, 0.02, _f(BOLT))
    p.drawPolygon(pts)
    if extra_hail:
        _pen(p, SNOW, 0.02, _f(SNOW))
        p.drawEllipse(QPointF(0.68, 0.82), 0.045, 0.045)


def _fog_lines(p):
    _pen(p, FOG, 0.05)
    for i, (x0, x1) in enumerate(((0.30, 0.74), (0.36, 0.80), (0.30, 0.68))):
        y = 0.78 + i * 0.085
        p.drawLine(QPointF(x0, y), QPointF(x1, y))


def _weather(kind, night, p):
    if kind == "clear":
        if night:
            _moon(p, 0.50, 0.50, 0.24)
        else:
            _sun_circle(p, 0.50, 0.50, 0.19)
    elif kind == "partly":
        if night:
            _moon(p, 0.63, 0.28, 0.15)
        else:
            _sun_circle(p, 0.65, 0.28, 0.13, with_rays=False)
            _pen(p, SUN, 0.04)
            for i in range(6):
                a = i * pi / 3
                p.drawLine(
                    QPointF(0.65 + cos(a) * 0.20, 0.28 + sin(a) * 0.20),
                    QPointF(0.65 + cos(a) * 0.26, 0.28 + sin(a) * 0.26),
                )
        _cloud(p, cx=0.46, cy=0.60, w=0.62)
    elif kind == "cloudy":
        _cloud(p, cx=0.38, cy=0.42, w=0.50, color=CLOUD_DARK)
        _cloud(p, cx=0.56, cy=0.58, w=0.60)
    elif kind == "fog":
        _cloud(p, cx=0.50, cy=0.46, w=0.62, color=CLOUD_DARK)
        _fog_lines(p)
    elif kind == "drizzle":
        _cloud(p, cx=0.50, cy=0.44, w=0.62)
        _pen(p, RAIN, 0.075)
        for x, y in ((0.42, 0.78), (0.56, 0.78), (0.49, 0.90), (0.63, 0.90)):
            p.drawEllipse(QPointF(x, y), 0.028, 0.028)
    elif kind in ("rain", "heavyrain"):
        _cloud(p, cx=0.50, cy=0.44, w=0.62)
        _rain_lines(p, n=3, heavy=(kind == "heavyrain"))
        if kind == "heavyrain":
            p.drawLine(QPointF(0.52, 0.74), QPointF(0.47, 0.92))
    elif kind in ("snow", "heavysnow"):
        _cloud(p, cx=0.50, cy=0.44, w=0.62)
        _snow(p)
        if kind == "heavysnow":
            _pen(p, SNOW, 0.035)
            for a in (0, pi / 3, 2 * pi / 3):
                p.drawLine(
                    QPointF(0.70 - cos(a) * 0.05, 0.74 - sin(a) * 0.05),
                    QPointF(0.70 + cos(a) * 0.05, 0.74 + sin(a) * 0.05),
                )
    elif kind in ("thunder", "thunderhail"):
        _cloud(p, cx=0.50, cy=0.42, w=0.62, color=CLOUD_DARK)
        _bolt(p, extra_hail=(kind == "thunderhail"))


class _UI:
    """Monochrome Begleitsymbole fuer die Detailbeschriftungen."""

    @staticmethod
    def _thermo(p):
        _pen(p, INK, 0.09)
        p.drawRoundedRect(QRectF(0.38, 0.06, 0.24, 0.62), 0.12, 0.12)
        p.drawEllipse(QPointF(0.50, 0.74), 0.15, 0.15)
        _pen(p, INK, 0.10)
        p.drawLine(QPointF(0.50, 0.70), QPointF(0.50, 0.30))

    @staticmethod
    def _droplet(p):
        path = QPainterPath()
        path.moveTo(QPointF(0.50, 0.05))
        path.cubicTo(QPointF(0.66, 0.34), QPointF(0.82, 0.46), QPointF(0.82, 0.64))
        path.arcTo(QRectF(0.18, 0.34, 0.64, 0.60), 0, -180)
        path.cubicTo(QPointF(0.34, 0.46), QPointF(0.34, 0.34), QPointF(0.50, 0.05))
        path.closeSubpath()
        p.drawPath(path.simplified())

    @staticmethod
    def _wind(p):
        for y, x0, x1 in ((0.28, 0.14, 0.72), (0.50, 0.26, 0.84), (0.72, 0.14, 0.60)):
            p.drawLine(QPointF(x0, y), QPointF(x1, y))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(0.60, 0.20, 0.22, 0.16), 90 * 16, -180 * 16)
        p.drawArc(QRectF(0.72, 0.42, 0.22, 0.16), 90 * 16, -180 * 16)

    @staticmethod
    def _umbrella(p):
        path = QPainterPath()
        path.moveTo(QPointF(0.10, 0.55))
        path.arcTo(QRectF(0.10, 0.10, 0.80, 0.90), 180, 180)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(0.50, 0.55), QPointF(0.50, 0.84))
        p.drawArc(QRectF(0.36, 0.76, 0.14, 0.20), 180 * 16, 180 * 16)

    @staticmethod
    def _gauge(p):
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(0.14, 0.16, 0.72, 0.72))
        p.drawLine(QPointF(0.50, 0.52), QPointF(0.70, 0.32))
        p.drawEllipse(QPointF(0.50, 0.52), 0.06, 0.06)
        for a in (135, 90, 45, 0, 225, 315, 270):
            rad = a * pi / 180
            p.drawLine(
                QPointF(0.50 + cos(rad) * 0.30, 0.52 - sin(rad) * 0.30),
                QPointF(0.50 + cos(rad) * 0.25, 0.52 - sin(rad) * 0.25),
            )

    @staticmethod
    def _sun(p):
        p.drawLine(QPointF(0.12, 0.80), QPointF(0.88, 0.80))
        _pen(p, INK, 0.085)
        for a in (0, 45, 90, 135, 180):
            rad = a * pi / 180
            p.drawLine(
                QPointF(0.50 + cos(rad) * 0.18, 0.80 - sin(rad) * 0.18),
                QPointF(0.50 + cos(rad) * 0.30, 0.80 - sin(rad) * 0.30),
            )
        p.drawEllipse(QPointF(0.50, 0.80), 0.16, 0.16)

    @staticmethod
    def _arrow(p, up=True):
        y0, y1 = (0.55, 0.10) if up else (0.10, 0.55)
        p.drawLine(QPointF(0.50, y0), QPointF(0.50, y1))
        head = QPolygonF([
            QPointF(0.38, y1 + (0.16 if up else -0.16)),
            QPointF(0.62, y1 + (0.16 if up else -0.16)),
            QPointF(0.50, y1 + (0.0 if up else 0.16)),
        ])
        p.drawPolygon(head)

    @staticmethod
    def _location(p):
        path = QPainterPath()
        path.moveTo(QPointF(0.30, 0.52))
        path.arcTo(QRectF(0.22, 0.06, 0.56, 0.92), 60, 240)
        path.lineTo(QPointF(0.50, 0.96))
        path.closeSubpath()
        p.drawPath(path.simplified())
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(0.50, 0.44), 0.13, 0.13)

    @staticmethod
    def _horizon_sun(p):
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(0.30, 0.30, 0.40, 0.40))
        _pen(p, INK, 0.10)
        p.drawLine(QPointF(0.08, 0.62), QPointF(0.92, 0.62))

    @staticmethod
    def _sunrise(p):
        _UI._horizon_sun(p)
        _UI._arrow(p, up=True)

    @staticmethod
    def _sunset(p):
        _UI._horizon_sun(p)
        _UI._arrow(p, up=False)

    # Aliase: mehrere Labels teilen sich ein Symbol
    _humidity = _droplet
    _uv = _sun
    _astro = _sunrise
    _gusts = _wind
    _precip = _umbrella
    _feels = _thermo
    _place = _location
