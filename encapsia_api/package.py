import datetime
import os
import pathlib
import re
import shutil
import string
import tarfile
import tempfile
from typing import Iterable

import toml

__all__ = ["PackageMaker"]


def _now() -> str:
    return datetime.datetime.isoformat(datetime.datetime.utcnow())


_VALID_NAME_REGEX = re.compile(r"^[A-Za-z_0-9\.]*$")


def _make_valid_name(text: str) -> str:
    valid_chars = set(
        string.ascii_lowercase + string.ascii_uppercase + string.digits + "_."
    )
    # Replace space with underscore
    text = text.replace(" ", "_")
    # Replace dash with underscore
    text = text.replace("-", "_")
    # Only include valid chars
    name = "".join(a for a in text if a in valid_chars)
    assert _VALID_NAME_REGEX.match(name) is not None
    return name


def extract_manifest(filename: pathlib.Path, manifest_name: str = "package.toml"):
    """Return the manifest as a dictionary from .tar.gz package."""
    with tarfile.open(filename, "r:gz") as tar:
        manifest = tar.extractfile(manifest_name)
        if manifest is None:
            raise ValueError(f"Missing manifest file: {manifest_name}")
        return toml.loads(manifest.read().decode())


class PackageMaker:

    """Generic maker of packages, intended to be used as a context manager."""

    def __init__(self, package_format: str, manifest_fields: dict):
        self.manifest = self._seed_manifest(package_format, manifest_fields)
        self.directory = pathlib.Path(tempfile.mkdtemp())

    def _seed_manifest(self, package_format: str, manifest: dict):
        if package_format != "1.0":
            raise ValueError(f"Unsupported package format: {package_format}")
        try:
            return {
                "package_format": "1.0",
                "type": {
                    "name": manifest["type"]["name"],
                    "description": manifest["type"]["description"],
                    "format": manifest["type"]["format"],
                },
                "instance": {
                    "name": manifest["instance"]["name"],
                    "description": manifest["instance"]["description"],
                    "version": manifest["instance"]["version"],
                    "created_by": manifest["instance"]["created_by"],
                    "created_on": manifest["instance"].get("created_on", _now()),
                },
            }
        except KeyError as e:
            raise ValueError(f"Missing required manifest field: {e!s} ")

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.directory)

    def add_to_manifest(self, **data):
        """Add data to type-specific section of the manifest."""
        type_name = self.manifest["type"]["name"]
        if type_name not in self.manifest:
            self.manifest[type_name] = {}
        self.manifest[type_name].update(data)

    def _add_manifest(self):
        filename = self.directory / "package.toml"
        with filename.open("w") as f:
            toml.dump(self.manifest, f)

    def _add_file_from_bytes_iterable(self, name: str, iterable: Iterable[bytes]):
        if name == "package.toml":
            raise ValueError(
                "The manifest file is added automatically and cannot be overridden."
            )
        filename = self.directory / name
        filename.parent.mkdir(parents=True, exist_ok=True)
        with filename.open("wb") as f:
            for data in iterable:
                f.write(data)

    def add_file_from_string(self, name: str, data: str):
        """Add a file of given name from string data. """
        self._add_file_from_bytes_iterable(name, (data.encode(),))

    def add_file_from_bytes(self, name: str, data: bytes):
        """Add a file of given name from bytes data."""
        self._add_file_from_bytes_iterable(name, (data,))

    def add_file_from_string_iterable(self, name: str, iterable: Iterable[str]):
        """Add a file of given name from bytes iterable."""
        self._add_file_from_bytes_iterable(name, (data.encode() for data in iterable))

    def add_file_from_bytes_iterable(self, name: str, iterable: Iterable[bytes]):
        """Add a file of given name from bytes iterable."""
        self._add_file_from_bytes_iterable(name, iterable)

    def add_all_files_from_directory(self, directory: pathlib.Path):
        if (directory / "package.toml").exists():
            raise ValueError(
                "The manifest file is added automatically and cannot be overridden."
            )
        # Ideally we would used shutil.copytree with the dirs_exit_ok option, but that's Python 3.8 and above.
        # So instead we do it by hand. Note the problem is only with the top level directory.
        for child in directory.iterdir():
            new_name = self.directory / os.path.relpath(child, directory)
            if child.is_file():
                child.rename(new_name)
            elif child.is_dir():
                shutil.copytree(child, new_name)
            else:
                raise ValueError(
                    f"Packages can only contain files or directories. The following is neither: {child}"
                )

    @property
    def package_filename(self) -> pathlib.Path:
        type_name = _make_valid_name(self.manifest["type"]["name"])
        instance_name = _make_valid_name(self.manifest["instance"]["name"])
        instance_version = _make_valid_name(self.manifest["instance"]["version"])
        return pathlib.Path(
            f"package-{type_name}-{instance_name}-{instance_version}.tar.gz"
        )

    def make_package(self, directory=pathlib.Path("/tmp")):
        """Return .tar.gz of newly created package in given directory."""
        self._add_manifest()
        filename = directory / self.package_filename

        def strip_root_dir(tarinfo):
            name = tarinfo.name[len(str(self.directory)) :].strip()
            assert not tarinfo.name.startswith("/")
            assert not name.startswith("/")
            assert "/" + tarinfo.name == str(self.directory / name)
            tarinfo.name = name
            return tarinfo

        with tarfile.open(filename, "w:gz") as tar:
            # Just doing tar.add(self.directory) creates problems with empty top level directory.
            # So iterate through the top level files and directories.
            for f in self.directory.iterdir():
                tar.add(f, filter=strip_root_dir)
        return filename
