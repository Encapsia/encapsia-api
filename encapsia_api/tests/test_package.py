import tarfile
import unittest

from encapsia_api import package


class TestPackageMaker(unittest.TestCase):
    def test_make_empty_package(self):
        with package.PackageMaker("test") as p:
            filename = p.make_package()
            self.assertEqual(filename.name, "package-test-0.0.1.tar.gz")
            with tarfile.open(filename, mode="r:gz") as tar:
                self.assertEqual(
                    set(m.name for m in tar.getmembers()), set(["package.toml"])
                )
