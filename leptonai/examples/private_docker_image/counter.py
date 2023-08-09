from leptonai.photon import Photon
import subprocess

import os


class Counter(Photon):
    image = "leptonai/base:latest"
    requirement_dependency = [
        "python-dotenv",
    ]
    extra_files = {"sample.txt": "sample.txt"}

    def init(self):
        self.counter = 0
        cwd = os.getcwd()
        files = os.listdir(cwd)
        print("Testing out extra file")
        for file in files:
            print(file)
            if file == "sample.txt":
                with open(file, "r") as input:
                    # Read the contents of the file into a variable
                    file_contents = input.read()
                print(file_contents)

        print("Testing out ENV var injection")
        print(os.environ.get("SOME_KEY", "some_key"))

    @Photon.handler("add")
    def add(self, x: int) -> int:
        self.counter += x
        return self.counter

    @Photon.handler("sub")
    def sub(self, x: int) -> int:
        self.counter -= x
        return self.counter

    @Photon.handler("ping")
    def ping(self, command: str) -> str:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            # Output of the uname command
            output = result.stdout.strip()
            print("System information:")
            print(output)
        else:
            print("Command execution failed.")
            print("Error message:")
            print(result.stderr)

        return result.stdout.strip()
