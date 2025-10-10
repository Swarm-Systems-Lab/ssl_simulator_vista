__all__ = [
    "get_grid_layout_path", 
    "list_available_layouts"
]

import importlib.resources as pkg_resources
from pathlib import Path

import ssl_vista

def get_grid_layout_path(layout_name: str) -> Path:
    """
    Return the path to a layout JSON file.
    Looks in package data under data/grid_layouts.
    """
    with pkg_resources.path(ssl_vista.data, "grid_layouts") as layouts_dir:
        candidate = layouts_dir / f"{layout_name}.json"
        if candidate.exists():
            return candidate
        else:
            # fallback: treat layout_name as relative path
            candidate = Path(layout_name)
            if candidate.exists():
                return candidate
            else:
                raise FileNotFoundError(f"Layout '{layout_name}' not found in grid_layouts or as a file.")
            

def list_available_layouts() -> list[str]:
    """
    Return a list of layout names available in data/grid_layouts (without the .json extension).
    Works in both editable mode and installed packages.
    """
    layouts = []
    # pkg_resources.path works for both installed and editable packages
    with pkg_resources.path(ssl_vista.data, "grid_layouts") as layouts_dir:
        for json_file in layouts_dir.glob("*.json"):
            layouts.append(json_file.stem)
    return sorted(layouts)