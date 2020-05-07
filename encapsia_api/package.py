import pathlib
import shutil
import tarfile
import tempfile
from typing import Iterable

import toml

__all__ = ["PackageMaker"]


class PackageMaker:

    """Generic maker of packages, intended to be used as a context manager."""

    def __init__(
        self, name, description="", version="0.0.1", created_by="unknown@encapsia.com"
    ):
        self.directory = pathlib.Path(tempfile.mkdtemp())
        self._files = []
        self._add_manifest(
            name=name, description=description, version=version, created_by=created_by
        )

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.directory)

    def _add_manifest(self, **kwargs):
        self._files.append("package.toml")
        filename = self.directory / "package.toml"
        with filename.open("w") as f:
            toml.dump(kwargs, f)

    def read_manifest(self):
        """Return the manifest as a dictionary."""
        return toml.load(self.directory / "package.toml")

    def _add_file(self, name: str, iterable: Iterable[bytes]):
        self._files.append(name)
        filename = self.directory / name
        filename.parent.mkdir(parents=True, exist_ok=True)
        with filename.open("wb") as f:
            for data in iterable:
                f.write(data)

    def add_file_from_string(self, name: str, data: str):
        """Add a file of given name from string data. """
        self._add_file(name, (data.encode(),))

    def add_file_from_bytes(self, name: str, data: bytes):
        """Add a file of given name from bytes data."""
        self._add_file(name, (data,))

    def add_file_from_string_iterable(self, name: str, iterable: Iterable[str]):
        """Add a file of given name from bytes iterable."""
        self._add_file(name, (data.encode() for data in iterable))

    def add_file_from_bytes_iterable(self, name: str, iterable: Iterable[bytes]):
        """Add a file of given name from bytes iterable."""
        self._add_file(name, iterable)

    def make_package(self, directory=pathlib.Path("/tmp")):
        """Return .tar.gz of newly created package in given directory."""
        manifest = self.read_manifest()
        name, version = manifest["name"], manifest["version"]
        filename = (
            pathlib.Path(tempfile.mkdtemp(dir=directory))
            / f"package-{name}-{version}.tar.gz"
        )
        filename.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(filename, "w:gz") as tar:
            for name in self._files:
                tar.add(self.directory / name, arcname=name)
        return filename
