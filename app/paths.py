from __future__ import annotations

import os
import sys
from pathlib import Path


# Root of the bundled PyInstaller package (when frozen) or the source tree
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
APP_SLUG = "RealEstateUtilityApp"


def _exe_dir() -> Path:
    """Directory containing the running exe (portable) or the source root."""
    if getattr(sys, "frozen", False):
        # PyInstaller onedir: sys.executable is .../УК_Учет/УК_Учет.exe
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def user_data_root() -> Path:
    exe_dir = _exe_dir()
    # Portable: keep data right next to the exe in a "data" subfolder
    if getattr(sys, "frozen", False):
        return exe_dir / "data"
    # Dev mode: use AppData so the dev folder stays clean
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_SLUG
    return exe_dir / "data_runtime"


RUNTIME_ROOT = user_data_root()
DATA_DIR = RUNTIME_ROOT / "data"
GENERATED_DIR = RUNTIME_ROOT / "generated"

DATA_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

