"""Resolve original flat source references in the organized repository.

Inputs/build outputs live at repository root; sources live in app folders.
No file creation, legacy execution, or account access happens on import.
"""
from pathlib import Path
import sys

_BASE = Path(__file__).resolve().parent.parent
_FOLDERS = ("notes", "calendars", "contacts")
_SOURCES = {}
for _folder in _FOLDERS:
    _directory = _BASE / _folder
    for _item in _directory.iterdir():
        if _item.name.startswith(".") or _item.name == "__pycache__":
            continue
        if _item.name in _SOURCES:
            raise RuntimeError("Duplicate source name: " + _item.name)
        _SOURCES[_item.name] = _item
    if str(_directory) not in sys.path:
        sys.path.append(str(_directory))

class ProjectRoot(type(Path())):
    def __truediv__(self, key):
        # Only source names directly below the old project root are remapped.
        # Subsequent path operations on build/input directories remain ordinary.
        parts = Path(key).parts
        if Path(self) == _BASE and parts and parts[0] in _SOURCES:
            return _SOURCES[parts[0]].joinpath(*parts[1:])
        return Path(self) / key

def project_root():
    return ProjectRoot(_BASE)
