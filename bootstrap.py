# Selbstinstallation: Dieses Modul läuft VOR allen anderen Imports in main.py
# und installiert fehlende Pakete automatisch beim ersten Start.
#
# Strategie:
#   1. Prüfen, ob das Import-Modul vorhanden ist (importlib).
#   2. Fehlt es: pip install (funktioniert in venv und normaler Python-Umgebung).
#   3. Schlägt pip fehl (z. B. Raspberry Pi OS Bookworm, PEP 668, oder
#      32-Bit-armv7, wo es keine PySide6-Wheels gibt): Fallback auf
#      sudo apt install python3-<paket>.
#
# Nach einem apt-Nachinstall muss die App einmal neu gestartet werden — das
# erledigt das Skript selbst, indem es sich als neuen Prozess erneut ausführt.
import importlib.util
import os
import subprocess
import sys

# (Importname, pip-Paket, apt-Paket)
PACKAGES = [
    ("PySide6", "PySide6>=6.7", "python3-pyside6"),
    ("matplotlib", "matplotlib>=3.8", "python3-matplotlib"),
    ("requests", "requests>=2.31", "python3-requests"),
]


def _is_available(import_name):
    return importlib.util.find_spec(import_name) is not None


def _pip_install(pip_package):
    """pip-Install mit Fallback auf --break-system-packages (PEP 668)."""
    base = [sys.executable, "-m", "pip", "install"]
    for extra in ([], ["--break-system-packages"]):
        try:
            if subprocess.run(
                base + extra + [pip_package],
                check=False,
            ).returncode == 0:
                return True
        except OSError as e:
            print(f"pip nicht nutzbar: {e}")
            return False
    return False


def _apt_install(apt_package):
    """Letzter Rettungsanker auf dem Pi: apt-Distribution-Paket."""
    print(f"pip fehlgeschlagen — versuche: sudo apt install {apt_package}")
    sudo = ["sudo"] if (hasattr(os, "geteuid") and os.geteuid() != 0) else []
    r = subprocess.run(sudo + ["apt-get", "install", "-y", apt_package], check=False)
    return r.returncode == 0


def _need_restart():
    """apt installierte einen neuen Paketsatz: gleiche App als neuer
    Interpreter-Prozess erneut starten, damit die neuen Pakete sichtbar sind."""
    os.execv(sys.executable, [sys.executable] + sys.argv)


def ensure_packages():
    missing = [(pip_pkg, apt_pkg) for mod, pip_pkg, apt_pkg in PACKAGES
               if not _is_available(mod)]
    if not missing:
        return False

    print("Fehlende Pakete werden installiert:")
    for pip_pkg, _ in missing:
        print(f"  - {pip_pkg}")

    apt_fallbacks = []   # (apt-Paket, pip-Paket), die pip nicht gelöst hat
    for pip_pkg, apt_pkg in missing:
        if _pip_install(pip_pkg):
            print(f"pip installiert: {pip_pkg}")
        else:
            apt_fallbacks.append((apt_pkg, pip_pkg))

    if apt_fallbacks:
        done_via_apt = []
        for apt_pkg, pip_pkg in apt_fallbacks:
            if _apt_install(apt_pkg):
                done_via_apt.append(pip_pkg)
        if done_via_apt:
            print("Über apt installiert:", ", ".join(done_via_apt))
            print("Starte die App neu, um die Pakete zu laden …")
            _need_restart()
        # pip UND apt haben versagt -> saubere Fehlermeldung statt Crash
        names = ", ".join(p for _, p in apt_fallbacks)
        sys.exit(
            f"Konnte folgende Pakete nicht automatisch installieren: {names}\n"
            "Bitte manuell installieren:\n"
            "  pip install PySide6 matplotlib requests\n"
            "oder auf Debian/Raspberry Pi OS:\n"
            "  sudo apt install python3-pyside6 python3-matplotlib python3-requests"
        )
    return True


if __name__ == "__main__":
    ensure_packages()
