import tarfile
import unittest

from encapsia_api import plugin


class TestPluginMaker(unittest.TestCase):
    def test_make_empty_plugin(self):
        with plugin.PluginMaker("test") as p:
            filename = p.make_plugin()
            self.assertEqual(filename.name, "plugin-test-0.0.1.tar.gz")
            with tarfile.open(filename, mode="r:gz") as tar:
                self.assertEqual(
                    set(m.name for m in tar.getmembers()),
                    set(["plugin-test", "plugin-test/plugin.toml"]),
                )
