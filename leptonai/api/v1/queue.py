from pydantic import BaseModel
from typing import Union, List

from .api_resource import APIResourse


class Queue(BaseModel):
    name: str


class QueueMessage(BaseModel):
    message: str


class QueueLength(BaseModel):
    length: int


class QueueAPI(APIResourse):
    def _to_name(self, name_or_queue: Union[str, Queue]) -> str:
        # Note: we do not use metadata.id_ or metadata.name here because these are not
        # the one used on the client side.
        return name_or_queue if isinstance(name_or_queue, str) else name_or_queue.name  # type: ignore

    def list_all(self) -> List[Queue]:
        """
        List queues in the current workspace.
        """
        response = self._get("/queue")
        return self.ensure_list(response, Queue)

    def create(self, name: str) -> Queue:
        """
        Create a queue in the current workspace. Note that queue creation is async,
        so when this method returns, the queue may not be ready yet. Use list_all()
        to check if the queue is ready. This function is idempotent, meaning that
        if the queue already exists, it will return the existing queue.
        """
        response = self._post("/queue", json={"name": name})
        self.ensure_ok(response)
        return Queue(name=name)

    def delete(self, name_or_queue: str) -> bool:
        """
        Delete a queue from the current workspace.
        """
        response = self._delete(f"/queue/{self._to_name(name_or_queue)}")
        return self.ensure_ok(response)

    def length(self, name_or_queue: str) -> QueueLength:
        """
        Get the length of a queue.
        """
        response = self._get(f"/queue/{self._to_name(name_or_queue)}/length")
        return self.ensure_type(response, QueueLength)

    def receive(self, name_or_queue: str) -> List[QueueMessage]:
        """
        Receives a message from a queue. Note that, although this method returns
        a list of messages, as of now it always only return one message. If the
        queue is empty, it will return an empty list.
        """
        response = self._get(f"/queue/{self._to_name(name_or_queue)}/messages")
        return self.ensure_list(response, QueueMessage)

    def send(self, name_or_queue: str, message: str) -> bool:
        """
        Put a message in the queue.
        """
        response = self._post(
            f"/queue/{self._to_name(name_or_queue)}/messages", json={"message": message}
        )
        return self.ensure_ok(response)
