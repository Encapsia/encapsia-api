import pathlib
import shutil
import tarfile
import tempfile
import toml


class PackageMaker:

    """Generic maker of packages, intended to be used as a context manager."""

    def __init__(self, name, **kwargs):
        self.directory = pathlib.Path(tempfile.mkdtemp())
        self._files = []
        self._add_manifest(name=name, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.directory)

    def _add_manifest(self, **kwargs):
        self._files.append("package.toml")
        data = dict(
            name=kwargs["name"],
            description=kwargs.get("description"),
            version=kwargs.get("version", "0.0.1"),
            created_by=kwargs.get("created_by", "unknown@encapsia.com"),
        )
        filename = self.directory / "package.toml"
        with filename.open("w") as f:
            toml.dump(data, f)

    def read_manifest(self):
        """Return the manifest as a dictionary."""
        return toml.load(self.directory / "package.toml")

    def add_file(self, name, data):
        """Add a file to the package of given name containing given data."""
        self._files.append(name)
        filename = self.directory / name
        filename.parent.mkdir(parents=True, exist_ok=True)
        with filename.open("w") as f:
            f.write(data)

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
