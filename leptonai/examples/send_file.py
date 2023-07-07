"""This is a simple example demonstrating how to create a Photon that
takes a file as input and how to use client to send the file to the
Photon."""

from leptonai.photon import Photon, FileParam
from leptonai.client import Client


# Server part
# Use `lep ph run -n send-file -m send_file.py:Server` to run the server
class Server(Photon):
    @Photon.handler()
    def cat(self, inputs: FileParam) -> str:
        """Return the content of the file."""
        return inputs.file.read().decode("utf-8")


# Client part
# Use `python send_file.py` to run the client
if __name__ == "__main__":
    client = Client("http://localhost:8080")
    print(client.cat(inputs=FileParam(open(__file__, "rb"))))
