import tarfile
import unittest

from encapsia_api import package


class TestMakeValidName(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(package._make_valid_name(""), "")

    def test_already_valid(self):
        self.assertEqual(package._make_valid_name("abc"), "abc")
        self.assertEqual(package._make_valid_name("aBc"), "aBc")
        self.assertEqual(package._make_valid_name("ABc"), "ABc")
        self.assertEqual(package._make_valid_name("ABc123"), "ABc123")
        self.assertEqual(package._make_valid_name("ABc_123"), "ABc_123")

    def test_hypens(self):
        self.assertEqual(package._make_valid_name("ABc-123"), "ABc_123")
        self.assertEqual(package._make_valid_name("-ABc-123"), "_ABc_123")
        self.assertEqual(package._make_valid_name("-ABc-123-"), "_ABc_123_")

    def test_spaces(self):
        self.assertEqual(package._make_valid_name("abc def"), "abc_def")
        self.assertEqual(package._make_valid_name("  abc def"), "__abc_def")
        self.assertEqual(package._make_valid_name("  abc def "), "__abc_def_")

    def test_newlines(self):
        self.assertEqual(package._make_valid_name("abc\ndef"), "abcdef")
        self.assertEqual(package._make_valid_name("\n\nabc\ndef"), "abcdef")
        self.assertEqual(package._make_valid_name("\n\nabc\ndef\n"), "abcdef")


class TestPackageMaker(unittest.TestCase):

    MANIFEST_FIELDS = dict(
        type_name="test-type",
        type_format="1.0",
        type_description="whatever",
        instance_name="test instance",
        instance_version="1.2.3",
        instance_created_by="fred",
    )
    PACKAGE_FILENAME = "package-test_type-test_instance-1.2.3.tar.gz"

    def test_supported_package_formats(self):
        package.PackageMaker("1.0", self.MANIFEST_FIELDS)
        with self.assertRaises(ValueError):
            package.PackageMaker("0.1", self.MANIFEST_FIELDS)
        with self.assertRaises(ValueError):
            package.PackageMaker("1.1", self.MANIFEST_FIELDS)
        with self.assertRaises(ValueError):
            package.PackageMaker("2.0", self.MANIFEST_FIELDS)

    def test_make_empty_package(self):
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p:
            filename = p.make_package()
            self.assertEqual(filename.name, self.PACKAGE_FILENAME)
            with tarfile.open(filename, mode="r:gz") as tar:
                self.assertEqual(
                    set(m.name for m in tar.getmembers()), set(["package.toml"])
                )

    def test_manifest_contents(self):
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p:
            filename = p.make_package()
        m = package.extract_manifest(filename)
        M = self.MANIFEST_FIELDS
        self.assertEqual(m["package_format"], "1.0")
        self.assertEqual(
            sorted(m.keys()), sorted(["package_format", "type", "instance"])
        )
        self.assertEqual(
            sorted(m["type"].keys()), sorted(["description", "name", "format"])
        )
        self.assertEqual(
            sorted(m["instance"].keys()),
            sorted(["name", "version", "created_by", "created_on"]),
        )
        self.assertEqual(m["type"]["name"], M["type_name"])
        self.assertEqual(m["type"]["format"], M["type_format"])
        self.assertEqual(
            m["type"]["description"], M["type_description"],
        )
        self.assertEqual(m["instance"]["name"], M["instance_name"])
        self.assertEqual(
            m["instance"]["version"], M["instance_version"],
        )
        self.assertEqual(
            m["instance"]["created_by"], M["instance_created_by"],
        )

    def test_cannot_overwrite_manifest_file(self):
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p:
            with self.assertRaises(ValueError):
                p.add_file_from_string("package.toml", "whatever")
