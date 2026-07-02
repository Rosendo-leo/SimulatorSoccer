"""Build the C++ strategy extensions.

Usage (from the bridge/ directory):
    python setup.py build_ext --inplace

Produces cpp_attacker.<abi>.pyd (Windows) / .so (Linux) next to this file,
importable as `bridge.cpp_attacker`.
"""
from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

ext_modules = [
    Pybind11Extension(
        "cpp_attacker",
        sources=["cpp/attacker.cpp"],
        include_dirs=["cpp"],
        cxx_std=17,
    ),
]

setup(
    name="rcj-cpp-strategies",
    version="0.1.0",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
