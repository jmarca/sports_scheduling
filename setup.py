#!/usr/bin/env python
import setuptools
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext
import io
import re

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sports_scheduling_via_ortools",
    version="0.0.1",
    author="James E. Marca",
    author_email="james@activimetrics.com",
    description="This program generates a feasible sports schedule, with various options allowed",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jmarca/sports_scheduling",
    packages=setuptools.find_packages(),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Utilities',
    ],
)
