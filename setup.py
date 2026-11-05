from __future__ import annotations

from setuptools import setup
from Cython.Build import cythonize
import numpy

setup(
    name='Quake2',
    ext_modules=cythonize("client/cl_cin_extras.pyx", compiler_directives={"language_level": "3"}),
    include_dirs=[numpy.get_include()],
)
