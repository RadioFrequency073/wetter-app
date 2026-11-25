# WMO-Wettercodes -> deutsche Beschreibung + Emoji-Icon.
# Quelle: Open-Meteo-Doku (weather_code, WMO standard).

WMO = {
    0:  ("Klar",                   "☀️", "🌙"),
    1:  ("Überwiegend klar",       "🌤️", "🌙"),
    2:  ("Teilweise bewölkt",      "⛅", "☁️"),
    3:  ("Bedeckt",                "☁️", "☁️"),
    45:  ("Nebel",                 "🌫️", "🌫️"),
    48:  ("Nebel mit Reif",        "🌫️", "🌫️"),
    51:  ("Leichter Nieselregen",  "🌦️", "🌧️"),
    53:  ("Nieselregen",           "🌦️", "🌧️"),
    55:  ("Starker Nieselregen",   "🌧️", "🌧️"),
    56:  ("Gefrierender Niesel",   "🌧️", "🌧️"),
    57:  ("Starker gefr. Niesel",  "🌧️", "🌧️"),
    61:  ("Leichter Regen",        "🌦️", "🌧️"),
    63:  ("Regen",                 "🌧️", "🌧️"),
    65:  ("Starker Regen",         "🌧️", "🌧️"),
    66:  ("Gefrierender Regen",    "🌧️", "🌧️"),
    67:  ("Starker gefr. Regen",   "🌧️", "🌧️"),
    71:  ("Leichter Schneefall",   "🌨️", "🌨️"),
    73:  ("Schneefall",            "🌨️", "🌨️"),
    75:  ("Starker Schneefall",    "❄️", "❄️"),
    77:  ("Schneegriesel",         "🌨️", "🌨️"),
    80:  ("Leichte Regenschauer",  "🌦️", "🌧️"),
    81:  ("Regenschauer",          "🌧️", "🌧️"),
    82:  ("Heftige Regenschauer",  "⛈️", "⛈️"),
    85:  ("Leichte Schneeschauer", "🌨️", "🌨️"),
    86:  ("Starke Schneeschauer",  "❄️", "❄️"),
    95:  ("Gewitter",              "⛈️", "⛈️"),
    96:  ("Gewitter mit Hagel",    "⛈️", "⛈️"),
    99:  ("Schweres Gewitter",     "⛈️", "⛈️"),
}


def describe(code, is_day=None):
    """WMO-Code -> (beschreibung, emoji). is_day=None liefert das Tag-Symbol,
    sonst Tag-(True)/Nacht-(False)-Variante."""
    desc, day_icon, night_icon = WMO.get(int(code or 0), ("Unbekannt", "❓", "❓"))
    if is_day is None or is_day:
        return desc, day_icon
    return desc, night_icon


def wind_direction(deg):
    """Grad -> Himmelsrichtung (deutsch, 8-seitig)."""
    dirs = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"]
    if deg is None:
        return "–"
    return dirs[int(((deg % 360) + 22.5) // 45) % 8]


def comfort_uv(uv):
    """UV-Index -> Kurzbeurteilung."""
    if uv is None:
        return "–"
    if uv < 3:
        return "niedrig"
    if uv < 6:
        return "mäßig"
    if uv < 8:
        return "hoch"
    if uv < 11:
        return "sehr hoch"
    return "extrem"
