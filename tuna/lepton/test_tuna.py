import sys
import unittest

import openai


class TestTuna(unittest.TestCase):
    def setUpClass():
        openai.api_base = "http://0.0.0.0:8080/api/v1"
        openai.api_key = "api-key"

    def setUp(self):
        self.model = "gpt-3.5-turbo"

    def test_list_models(self):
        models = openai.Model.list()
        self.assertIn("gpt-3.5-turbo", [model["id"] for model in models["data"]])

    def test_chat_completion_stream(self):
        sys_prompt = """
The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.
"""
        # Create a completion
        completion = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": "tell me a short story"},
            ],
            stream=True,
            max_tokens=64,
        )
        for chunk in completion:
            content = chunk["choices"][0]["delta"].get("content")
            if content:
                sys.stdout.write(content)
                sys.stdout.flush()
        sys.stdout.write("\n")

    def test_chat_completion(self):
        sys_prompt = """
The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.
"""
        completion = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": "tell me a long story"},
            ],
            max_tokens=64,
        )
        print(completion)

    def test_embedding(self):
        embedding = openai.Embedding.create(
            model=self.model,
            input=["Hello, world!", "How are you?"],
        )
        dim = len(embedding["data"][0]["embedding"])
        print(f"Embedding dimension: {dim}")


if __name__ == "__main__":
    unittest.main()
