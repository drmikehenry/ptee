#!/usr/bin/env python
# coding=utf-8

from setuptools import setup, find_packages
import os

NAME = "ptee"


def open_file(name):
    return open(os.path.join(os.path.dirname(__file__), name))


__version__ = None
for line in open("src/{}.py".format(NAME), encoding="utf-8"):
    if line.startswith("__version__"):
        __version__ = line.split("=")[1].strip().replace('"', "")
        break

setup(
    name=NAME,
    version=__version__,
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[NAME],
    python_requires=">=3.5",
    install_requires=["blessed",],
    entry_points={"console_scripts": ["ptee=ptee:main",],},
    description=(
        '"Progress tee", an enhanced "tee" program with in-place '
        + 'overwriting of "status".'
    ),
    long_description=open_file("README.rst").read(),
    keywords="progress tee in-place overwriting status",
    url="https://github.com/drmikehenry/ptee",
    author="Michael Henry",
    author_email="drmikehenry@drmikehenry.com",
    license="MIT",
    zip_safe=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Text Processing :: Filters",
        "Topic :: Utilities",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
