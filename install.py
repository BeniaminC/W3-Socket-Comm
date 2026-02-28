import os
import logging
import winreg


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def enable_webui_in_registry(enable: bool = True) -> bool:
    """Mirrors setup.ts to allow the Warcraft III client to load local webui files."""
    try:
        # Target: HKCU\SOFTWARE\Blizzard Entertainment\Warcraft III
        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, r"SOFTWARE\Blizzard Entertainment\Warcraft III"
        )
        winreg.SetValueEx(
            key, "Allow Local Files", 0, winreg.REG_DWORD, 1 if enable else 0
        )
        winreg.CloseKey(key)
        logger.info(f"Registry 'Allow Local Files' set to {enable}")
        return True
    except Exception as e:
        logger.error(f"Failed to modify registry: {e}")
        return False


def get_warcraft_install_location() -> str:
    """Mirrors setup.ts to find the installation directory via Registry."""
    reg_install_key = (
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Warcraft III"
    )
    backup_reg_install_key = (
        r"SOFTWARE\WOW6432Node\Blizzard Entertainment\Warcraft III\Capabilities"
    )

    # Try primary uninstaller key
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_install_key)
        loc, _ = winreg.QueryValueEx(key, "InstallLocation")
        winreg.CloseKey(key)
        if loc:
            return str(loc)
    except OSError:
        pass

    # Try backup capabilities key
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, backup_reg_install_key)
        app_icon, _ = winreg.QueryValueEx(key, "ApplicationIcon")
        winreg.CloseKey(key)
        if app_icon:
            # app_icon is typically: "C:\Program Files (x86)\Warcraft III\_retail_\x86_64\Warcraft III.exe"
            # We move up 3 directories to get the base install path safely without string slicing
            base_path = str(app_icon).strip('"')
            return os.path.dirname(os.path.dirname(os.path.dirname(base_path)))
    except OSError:
        pass

    # Fallback if both fail
    return r"C:\Program Files (x86)\Warcraft III"
