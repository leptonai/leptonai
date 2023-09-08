import glob
import os
import sys

try:
    import torch  # noqa: F401
except ImportError:
    print("Please install torch first.")
    sys.exit(1)

try:
    from torch.cuda.memory import CUDAPluggableAllocator  # noqa: F401
except ImportError:
    print("Your torch version is too old. Please upgrade to v2.0.0 or higher.")
    sys.exit(1)

from setuptools import setup, find_packages
from torch.utils import cpp_extension

setup(
    name="tum",
    version="0.0.1",
    author="Lepton AI Inc.",
    author_email="dev@lepton.ai",
    packages=find_packages(),
    ext_modules=[
        cpp_extension.CUDAExtension(
            name="tum._tum",
            sources=glob.glob("./tum/*.cc", recursive=True),
            include_dirs=[os.path.dirname(os.path.abspath(__file__))],
        )
    ],
    install_requires=["torch"],
    cmdclass={"build_ext": cpp_extension.BuildExtension},
)
