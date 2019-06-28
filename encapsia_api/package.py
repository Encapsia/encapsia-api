import pathlib
import shutil
import tarfile
import tempfile
import types

import toml


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

    def _add_file(self, name, chunks, mode):
        """Add a file to the package of given name containing given data."""
        self._files.append(name)
        filename = self.directory / name
        filename.parent.mkdir(parents=True, exist_ok=True)
        with filename.open(f"w{mode}") as f:
            for chunk in chunks:
                f.write(chunk)

    def add_file(self, name, data):
        """Add a file to the package of given name containing given data.

        data should be a string object.
        """
        self._add_file(name, (data, ), "t")

    def add_file_from_bytes(self, name, data):
        """Add a file to the package of given name containing given data.

        data should be a bytes object.
        """
        self._add_file(name, (data, ), "b")

    def add_file_from_chunks(self, name, chunks, mode=None):
        """Add a file to the package of given name containing given data.

        data should be an iterable returning chunks of the file's data.
        """
        if mode not in ("t", "b"):
            raise ValueError(
                "Must provide write mode (t or b) suitable for "
                "data returned by data_source"
            )
        self._add_file(name, chunks, mode)

    def make_package(self, directory=pathlib.Path("/tmp/ice")):
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
