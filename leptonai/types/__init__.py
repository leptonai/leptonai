"""
Shared lightweight data types for the Lepton AI library, such as :class:`File`
for passing file content to and from deployments.
"""

from .file import File
from .fileparam import FileParam

__all__ = ["File", "FileParam"]
