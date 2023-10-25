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
        # Test rsync: rsync the whole thing
        cache.rsync("")
        self.assertTrue(os.path.exists("/tmp/leptonai-s3cache-test/folder/foo.txt"))
        with open("/tmp/leptonai-s3cache-test/folder/foo.txt", "r") as f:
            self.assertEqual(f.read(), "bar\n")


if __name__ == "__main__":
    unittest.main()
