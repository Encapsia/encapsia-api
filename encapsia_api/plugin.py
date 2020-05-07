import io
import pathlib
import shutil
import tarfile
import tempfile

import toml

from .util import get_api_from_api_or_host, make_uuid

__all__ = ["PluginMaker"]


def _create_targz_as_bytes(directory):
    data = io.BytesIO()
    with tarfile.open(mode="w:gz", fileobj=data) as tar:
        tar.add(directory, arcname=directory.name)
    return data.getvalue()


class PluginMaker:

    """Generic maker of plugins, intended to be used as a context manager."""

    def __init__(self, name, directory=None, **kwargs):
        self.directory = pathlib.Path(directory or tempfile.mkdtemp())
        self._add_manifest(name=name, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.directory)

    def get_directory(self):
        return self.directory

    def _add_manifest(self, **kwargs):
        data = dict(kwargs)
        # All values are passed through to the manifest but
        # ensure certain values are set and supply some defaults.
        data.update(
            dict(
                name=data["name"],
                description=data.get("description"),
                version=data.get("version", "0.0.1"),
                created_by=data.get("created_by", "unknown@encapsia.com"),
                n_task_workers=data.get("n_task_workers", 1),
            )
        )
        filename = self.directory / "plugin.toml"
        with filename.open("w") as f:
            toml.dump(data, f)

    def read_manifest(self):
        return toml.load(self.directory / "plugin.toml")

    def add_view_file(self, name, sql):
        filename = self.directory / "views" / name
        if filename.suffix != ".sql":
            filename = filename.with_suffix(".sql")
        filename.parent.mkdir(parents=True, exist_ok=True)
        with filename.open("w") as f:
            f.write(sql)

    def dev_install(self, api_or_host):
        api = get_api_from_api_or_host(api_or_host)
        return api.run_plugins_task(
            "dev_update_plugin", dict(), data=_create_targz_as_bytes(self.directory)
        )

    def dev_uninstall(self, api_or_host):
        api = get_api_from_api_or_host(api_or_host)
        name = self.read_manifest()["name"]
        return api.run_plugins_task("dev_destroy_namespace", dict(namespace=name))

    def make_plugin(self, directory=pathlib.Path("/tmp")):
        """Return .tar.gz of newly created plugin in given directory."""
        manifest = self.read_manifest()
        name, version = manifest["name"], manifest["version"]
        temp_directory = pathlib.Path(tempfile.mkdtemp(dir=directory))
        filename = temp_directory / f"plugin-{name}-{version}.tar.gz"
        filename.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(filename, "w:gz") as tar:
            tar.add(self.directory, arcname=f"plugin-{name}")
        return filename

    def make_and_upload_plugin(self, api_or_host, directory=pathlib.Path("/tmp")):
        """Make plugin, upload as blob, and return local filename and URL."""
        filename = self.make_plugin(directory=directory)
        blob_data = filename.read_bytes()
        api = get_api_from_api_or_host(api_or_host)
        response = api.put(
            ("blobs", make_uuid()),
            data=blob_data,
            extra_headers={"Content-type": "application/x-tar"},
        )
        return filename, response["result"]["url"]
