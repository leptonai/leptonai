from locust import HttpUser, task


class GPT2User(HttpUser):
    def _send_request(self):
        self.client.post(
            "/run", json={"inputs": "a cat", "temperature": 0.7, "do_sample": True}
        )

    def on_start(self):
        self._send_request()

    @task
    def bench(self):
        self._send_request()
