import os
from setuptools import setup, find_packages

with open(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "requirements.txt")
) as f:
    requirements = f.read().splitlines()

setup(
    name="vectordb",
    version="0.1",
    description="Lepton package",
    author="Lepton AI Inc.",
    author_email="dev@lepton.ai",
    url="https://lepton.ai",
    packages=find_packages(),
    install_requires=requirements,
)
