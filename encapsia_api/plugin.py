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
        self.add_manifest(name=name, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.directory)

    def get_directory(self):
        return self.directory

    def add_manifest(self, **kwargs):
        data = dict(
            name=kwargs["name"],
            description=kwargs.get("description"),
            version=kwargs.get("version", "0.0.1"),
            created_by=kwargs.get("created_by", "unknown@encapsia.com"),
            n_task_workers=kwargs.get("n_task_workers", 1),
            reset_on_install=kwargs.get("reset_on_install", True),
        )
        filename = self.directory / "plugin.toml"
        with filename.open("w") as f:
            toml.dump(data, f)

    def read_manifest(self):
        return toml.load(self.directory / "plugin.toml")

    def add_view(self, name, sql):
        filename = self.directory / "views" / name
        if filename.suffix != ".sql":
            filename = filename.with_suffix(".sql")
        filename.parent.mkdir(parents=True, exist_ok=True)
        with filename.open("w") as f:
            f.write(sql)

    def dev_install(self, api_or_host, print_output=True):
        api = get_api_from_api_or_host(api_or_host)
        api.run_plugins_task(
            "dev_update_plugin",
            dict(),
            data=_create_targz_as_bytes(self.directory),
            print_output=print_output,
        )

    def dev_uninstall(self, api_or_host, print_output=True):
        api = get_api_from_api_or_host(api_or_host)
        name = self.read_manifest()["name"]
        api.run_plugins_task(
            api,
            "dev_destroy_namespace",
            dict(namespace=name),
            print_output=print_output,
        )

    def make_plugin(self, api_or_host):
        """Make plugin, upload as blob, and return local filename and URL."""
        manifest = self.read_manifest()
        name, version = manifest["name"], manifest["version"]
        temp_directory = pathlib.Path(tempfile.mkdtemp())
        filename = temp_directory / f"plugin-{name}-{version}.tar.gz"
        tar = tarfile.open(filename, "w:gz")
        tar.add(self.directory, arcname=f"plugin-{name}")
        tar.close()
        with filename.open("rb") as f:
            blob_data = f.read()
            api = get_api_from_api_or_host(api_or_host)
            response = api.call_api(
                "put",
                ("blobs", make_uuid()),
                data=blob_data,
                extra_headers={"Content-type": "application/x-tar"},
                return_json=True,
                check_json_status=True,
            )
            return filename, response["result"]["url"]
