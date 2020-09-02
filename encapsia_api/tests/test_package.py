import pathlib
import tarfile
import tempfile
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
        type=dict(name="test-type", format="1.0", description="whatever"),
        instance=dict(
            name="test instance", description="", version="1.2.3", created_by="fred"
        ),
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
            sorted(["name", "description", "version", "created_by", "created_on"]),
        )
        self.assertEqual(m["type"]["name"], M["type"]["name"])
        self.assertEqual(m["type"]["format"], M["type"]["format"])
        self.assertEqual(
            m["type"]["description"],
            M["type"]["description"],
        )
        self.assertEqual(m["instance"]["name"], M["instance"]["name"])
        self.assertEqual(
            m["instance"]["version"],
            M["instance"]["version"],
        )
        self.assertEqual(
            m["instance"]["created_by"],
            M["instance"]["created_by"],
        )

    def test_cannot_overwrite_manifest_file(self):
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p:
            with self.assertRaises(ValueError):
                p.add_file_from_string("package.toml", "whatever")

    def test_add_files_from_string(self):
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p:
            p.add_file_from_string("a.txt", "foo")
            p.add_file_from_string("b.txt", "bar")
            filename = p.make_package()
            with tarfile.open(filename, mode="r:gz") as tar:
                self.assertEqual(
                    set(m.name for m in tar.getmembers()),
                    set(["a.txt", "b.txt", "package.toml"]),
                )

    def test_add_files_from_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir = pathlib.Path(tmp_dir)
            (tmp_dir / "a.txt").write_text("foo")
            (tmp_dir / "a_directory").mkdir()
            (tmp_dir / "a_directory" / "b.txt").write_text("bar")
            with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p:
                p.add_all_files_from_directory(tmp_dir)
                filename = p.make_package()
                with tarfile.open(filename, mode="r:gz") as tar:
                    self.assertEqual(
                        set(m.name for m in tar.getmembers()),
                        set(
                            [
                                "a.txt",
                                "a_directory",
                                "a_directory/b.txt",
                                "package.toml",
                            ]
                        ),
                    )
