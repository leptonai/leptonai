import os
import shutil
import unittest


@unittest.skipIf(
    not os.path.exists(os.path.expanduser("~/.aws/credentials")),
    "No AWS credentials found.",
)
class TestS3Cache(unittest.TestCase):
    def tearDown(self):
        # Remove the folder "/tmp/leptonai-s3cache-test" and any contents
        shutil.rmtree("/tmp/leptonai-s3cache-test", ignore_errors=True)

    def test_s3cache(self):
        # We import the package here to avoid the boto3 dependency if the test is not run
        # (e.g. if the user does not have AWS credentials)
        from leptonai.util.s3cache import S3Cache

        cache = S3Cache(
            bucket="leptonai-s3cache-test", local_folder="/tmp/leptonai-s3cache-test"
        )
        # Test get
        local_path = cache.get("answer.txt")
        self.assertTrue(os.path.exists(local_path))
        with open(local_path, "r") as f:
            self.assertEqual(f.read(), "42\n")

        # Modify the local file.
        with open("/tmp/leptonai-s3cache-test/answer.txt", "w") as f:
            f.write("1337\n")

        # Test get: should not download the file again if we don't set check_file.
        local_path = cache.get("answer.txt")
        self.assertTrue(os.path.exists(local_path))
        with open(local_path, "r") as f:
            self.assertEqual(f.read(), "1337\n")

        # Test get: should download the file again if we set check_file.
        local_path = cache.get("answer.txt", check_file=True)
        self.assertTrue(os.path.exists(local_path))
        with open(local_path, "r") as f:
            self.assertEqual(f.read(), "42\n")

        # Modify the local file but with the same size.
        with open("/tmp/leptonai-s3cache-test/answer.txt", "w") as f:
            f.write("43\n")

        # Test get: should not download the file again if we don't set check_file.
        local_path = cache.get("answer.txt")
        self.assertTrue(os.path.exists(local_path))
        with open(local_path, "r") as f:
            self.assertEqual(f.read(), "43\n")

        # Test get: should download the file again if we set check_file, as it catches file modification time.
        local_path = cache.get("answer.txt", check_file=True)
        self.assertTrue(os.path.exists(local_path))
        with open(local_path, "r") as f:
            self.assertEqual(f.read(), "42\n")

        # Test rsync: rsync the whole thing
        cache.rsync("")
        self.assertTrue(os.path.exists("/tmp/leptonai-s3cache-test/folder/foo.txt"))
        with open("/tmp/leptonai-s3cache-test/folder/foo.txt", "r") as f:
            self.assertEqual(f.read(), "bar\n")

        # Similar to get, we check file modifications
        with open("/tmp/leptonai-s3cache-test/folder/foo.txt", "w") as f:
            f.write("baz\n")

        # Test rsync: should not download the file again if we don't set check_file.
        cache.rsync("")
        self.assertTrue(os.path.exists("/tmp/leptonai-s3cache-test/folder/foo.txt"))
        with open("/tmp/leptonai-s3cache-test/folder/foo.txt", "r") as f:
            self.assertEqual(f.read(), "baz\n")

        # Test rsync: should download the file again if we set check_file.
        cache.rsync("", check_file=True)
        self.assertTrue(os.path.exists("/tmp/leptonai-s3cache-test/folder/foo.txt"))
        with open("/tmp/leptonai-s3cache-test/folder/foo.txt", "r") as f:
            self.assertEqual(f.read(), "bar\n")


if __name__ == "__main__":
    unittest.main()
