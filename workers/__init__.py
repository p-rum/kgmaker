"""Trusted optional worker resources shipped as ``kgmaker_workers``.

Importing this package never builds workers, installs dependencies, or launches
a runtime. Release builders explicitly prepare the optional artifacts before
building a wheel; a source-only wheel carries the scripts and pinned inputs.
"""
