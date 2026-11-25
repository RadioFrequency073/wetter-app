# Selbstinstallation: Dieses Modul läuft VOR allen anderen Imports in main.py
# und installiert fehlende Pakete automatisch beim ersten Start.
#
# Strategie:
#   1. Prüfen, ob das Import-Modul vorhanden ist (importlib).
#   2. Fehlt es: pip install. Auf Debian/Raspberry Pi OS (Bookworm, PEP 668)
#      wird --break-system-packages direkt mitgegeben, damit es beim ersten
#      Versuch klappt und keine Fehlermeldung von pip übrig bleibt; die
#      Pakete landen in ~/.local (user site-packages).
#   3. Schlägt pip fehl (z. B. 32-Bit Raspberry Pi OS, wo es keine
#      PySide6-Wheels gibt): Fallback auf sudo apt install python3-<paket>.
#   4. Danach startet sich die App als neuer Prozess neu — Python sieht neu
#      installierte Pakete erst in einem frischen Interpreter. Eine Umgebungs-
#      variable verhindert eine Endlosschleife, falls dann immer noch etwas
#      fehlt.
import importlib.util
import os
import subprocess
import sysconfig

# (Importname, pip-Paket, apt-Paket)
PACKAGES = [
    ("PySide6", "PySide6>=6.7", "python3-pyside6"),
    ("matplotlib", "matplotlib>=3.8", "python3-matplotlib"),
    ("requests", "requests>=2.31", "python3-requests"),
]

RESTART_MARKER = "WETTERAPP_BOOTSTRAP_RESTARTED"


def _is_available(import_name):
    return importlib.util.find_spec(import_name) is not None


def _is_externally_managed():
    """Debian/Raspberry Pi OS ab Bookworm markiert die Python-Installation
    als 'externally managed' (PEP 668) — dann braucht pip sofort den
    --break-system-packages-Schalter."""
    return os.path.exists(os.path.join(sysconfig.get_path("stdlib"), "EXTERNALLY-MANAGED"))


def _pip_install(pip_package):
    base = [sys.executable, "-m", "pip", "install", "-q"]
    if _is_externally_managed():
        base.append("--break-system-packages")
    try:
        return subprocess.run(base + [pip_package], check=False).returncode == 0
    except OSError:
        return False


def _apt_install(apt_package):
    """Letzter Rettungsanker auf dem Pi: apt-Distributions-Paket."""
    print(f"pip fehlgeschlagen — versuche: sudo apt install {apt_package}")
    sudo = ["sudo"] if (hasattr(os, "geteuid") and os.geteuid() != 0) else []
    try:
        return subprocess.run(
            sudo + ["apt-get", "install", "-y", apt_package], check=False
        ).returncode == 0
    except OSError:
        return False


def ensure_packages():
    missing = [(pip_pkg, apt_pkg) for mod, pip_pkg, apt_pkg in PACKAGES
               if not _is_available(mod)]
    if not missing:
        return False

    # Schutz gegen Endlosschleife: Wenn wir nach einem Neustart immer noch
    # Pakete vermissen, ist die Automatik gescheitert -> klare Meldung.
    if os.environ.get(RESTART_MARKER) == "1":
        names = ", ".join(p for p, _ in missing)
        sys.exit(
            f"Nach der Installation fehlen immer noch: {names}\n"
            "Bitte manuell installieren:\n"
            "  pip install PySide6 matplotlib requests\n"
            "oder auf Debian/Raspberry Pi OS:\n"
            "  sudo apt install python3-pyside6 python3-matplotlib python3-requests"
        )

    print("Fehlende Pakete werden installiert:")
    for pip_pkg, _ in missing:
        print(f"  - {pip_pkg}")

    failed = []
    for pip_pkg, apt_pkg in missing:
        if _pip_install(pip_pkg):
            print(f"pip installiert: {pip_pkg}")
        elif _apt_install(apt_pkg):
            print(f"apt installiert: {apt_pkg}")
        else:
            failed.append(pip_pkg)

    if failed:
        names = ", ".join(failed)
        sys.exit(
            f"Konnte folgende Pakete nicht automatisch installieren: {names}\n"
            "Bitte manuell installieren:\n"
            "  pip install PySide6 matplotlib requests\n"
            "oder auf Debian/Raspberry Pi OS:\n"
            "  sudo apt install python3-pyside6 python3-matplotlib python3-requests"
        )

    # Neustart als frischer Prozess, damit Python die neuen Pakete findet.
    os.environ[RESTART_MARKER] = "1"
    print("Alle Pakete installiert — App startet neu …\n")
    os.execv(sys.executable, [sys.executable] + sys.argv)
