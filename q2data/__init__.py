"""Read and write Quake II data files.

A self-contained library: it depends only on numpy and Pillow, never prints,
and keeps no global state. Loaders take bytes (or a path, or a
:class:`~q2data.filesystem.FileSystem`) and return plain dataclasses with numpy
arrays. Problems with a file raise :class:`FormatError`; problems that Quake II
tolerates are returned as warnings on the loaded object.
"""

from q2data.errors import FormatError

__all__ = ["FormatError"]
