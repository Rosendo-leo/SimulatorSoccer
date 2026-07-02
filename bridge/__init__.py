"""C++ strategy bridge (pybind11).

Compiled extensions land in this package (e.g. bridge/cpp_attacker.pyd)
and are used like any Python strategy:

    python -m sim --strategy bridge.cpp_attacker

Build them with:  cd bridge && python setup.py build_ext --inplace
"""
