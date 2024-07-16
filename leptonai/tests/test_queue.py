import random
import string
import time

from loguru import logger

from leptonai.api.v0 import workspace as workspace_api
from leptonai.queue import Queue, Empty
import unittest


def random_name():
    return "".join(random.choice(string.ascii_lowercase) for _ in range(8))


@unittest.skipIf(
    workspace_api.WorkspaceInfoLocalRecord.get_current_workspace_id() is None,
    "No login info. Skipping test.",
)
class TestQueue(unittest.TestCase):
    def setUp(self):
        self.prefix = "testws-" + random_name()
        logger.debug(f"Setting up test with queue name {self.prefix}")
        self.queue_instance = Queue(self.prefix, create_if_not_exists=True)
        logger.debug("Queue created")

    def tearDown(self):
        logger.debug(f"Tearing down test with queue name {self.prefix}")
        Queue.delete_queue(self.queue_instance)
        logger.debug("Queue deleted")

    def test_create_delete_queue(self):
        logger.debug("testing creation and deletion apis.")
        old_len = len(Queue.list_queue())
        self.assertGreater(old_len, 0)
        logger.debug("Testing create/delete")
        logger.debug("Testing create/delete with existing queue")
        with self.assertRaises(ValueError):
            _ = Queue(self.prefix, create_if_not_exists=False, error_if_exists=True)
        logger.debug("Testing create/delete with non-existing queue")
        with self.assertRaises(ValueError):
            _ = Queue(
                self.prefix + "2", create_if_not_exists=False, error_if_exists=False
            )
        new_len = len(Queue.list_queue())
        self.assertEqual(old_len, new_len)

    def test_length(self):
        logger.debug("Testing length")
        logger.debug("Testing length with empty queue")
        self.assertEqual(self.queue_instance.length(), 0)
        logger.debug("Testing length with non-empty queue")

        self.queue_instance.send("test")
        remain_wait = 50
        while self.queue_instance.length() != 1 and remain_wait > 0:
            time.sleep(0.1)
            remain_wait -= 1
        if remain_wait == 0:
            self.fail("Queue length did not become 1 after 5 seconds")

        self.queue_instance.send("test2")
        remain_wait = 50
        while self.queue_instance.length() != 2 and remain_wait > 0:
            time.sleep(0.1)
            remain_wait -= 1
        if remain_wait == 0:
            self.fail("Queue length did not become 2 after 5 seconds")

        received = []
        received.append(self.queue_instance.receive())
        remain_wait = 50
        while self.queue_instance.length() != 1 and remain_wait > 0:
            time.sleep(0.1)
            remain_wait -= 1
        if remain_wait == 0:
            self.fail("Queue length did not become 1 after 5 seconds")

        received.append(self.queue_instance.receive())
        remain_wait = 50
        while self.queue_instance.length() != 0 and remain_wait > 0:
            time.sleep(0.1)
            remain_wait -= 1
        if remain_wait == 0:
            self.fail("Queue length did not become 0 after 5 seconds")
        self.assertEqual(sorted(received), ["test", "test2"])

    def test_send_receive(self):
        logger.debug("Testing receive/send")

        logger.debug("Testing receive with empty queue")
        with self.assertRaises(Empty):
            logger.debug(self.queue_instance.receive())

        message = "this is a test"
        logger.debug("Testing send")
        self.queue_instance.send(message)
        logger.debug("Testing receive")
        self.assertEqual(self.queue_instance.receive(), message)

        logger.debug("Testing receive with now empty queue")
        with self.assertRaises(Empty):
            _ = self.queue_instance.receive()

        logger.debug("Testing fifo behavior. Sending...")
        messages = ["message_1", "message_2", "message_3"]
        start = time.time()
        for m in messages:
            self.queue_instance.send(m)
        # Receive messages, ignoring empty message, and check if the order is correct
        logger.debug("Send done. Receiving...")
        received = []
        while len(received) < len(messages):
            try:
                received.append(self.queue_instance.receive())
                logger.debug(f"Received {received[-1]}")
            except Empty:
                pass
        logger.debug(
            f"Received {len(received)} messages in {time.time() - start} seconds."
        )
        self.assertEqual(messages, received)
        with self.assertRaises(Empty):
            _ = self.queue_instance.receive()


if __name__ == "__main__":
    unittest.main()
