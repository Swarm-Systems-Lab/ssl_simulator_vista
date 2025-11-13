import importlib.resources as pkg_resources
from pathlib import Path

import ssl_vista

class DataManager:
    """A class to manage data files and layouts in the SSL Visualization Tool."""

    @staticmethod
    def _get_file_path(base_dir: str, file_name: str, extension: str) -> Path:
        """
        Generic method to get the path to a file in a specified directory.
        Falls back to treating file_name as a relative path if not found in base_dir.
        """
        with pkg_resources.path(ssl_vista.data, base_dir) as dir_path:
            candidate = dir_path / f"{file_name}.{extension}"
            if candidate.exists():
                return candidate
            else:
                # fallback: treat file_name as relative path
                candidate = Path(file_name)
                if candidate.exists():
                    return candidate
                else:
                    raise FileNotFoundError(f"File '{file_name}.{extension}' not found in {base_dir}.")

    @staticmethod
    def get_grid_layout_path(layout_name: str) -> Path:
        """
        Return the path to a layout JSON file.
        Looks in package data under data/grid_layouts.
        """
        return DataManager._get_file_path("grid_layouts", layout_name, "json")

    @staticmethod
    def get_sample_path(sample_name: str) -> Path:
        """
        Return the path to a sample CSV file.
        Looks in package data under data/samples.
        """
        return DataManager._get_file_path("samples", sample_name, "csv")

    @staticmethod
    def _list_available_files(base_dir: str, extension: str) -> list[str]:
        """
        Generic method to list available files in a specified directory.
        Returns file names without the extension.
        """
        files = []
        with pkg_resources.path(ssl_vista.data, base_dir) as dir_path:
            for file in dir_path.glob(f"*.{extension}"):
                files.append(file.stem)
        return sorted(files)

    @staticmethod
    def list_available_layouts() -> list[str]:
        """
        Return a list of layout names available in data/grid_layouts (without the .json extension).
        Works in both editable mode and installed packages.
        """
        return DataManager._list_available_files("grid_layouts", "json")

    @staticmethod
    def list_available_samples() -> list[str]:
        """
        Return a list of sample names available in data/samples (without the .csv extension).
        Works in both editable mode and installed packages.
        """
        return DataManager._list_available_files("samples", "csv")