#!/usr/bin/python
# -*- coding: utf-8 -*-

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="clickhouse_ddl",
    version="1.0.7",
    author="ish1mura",
    author_email="ek.dummy@gmail.com",
    description="Clickhouse metadata (DDL) grabber",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ish1mura/clickhouse_ddl",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'clickhouse_driver',
    ],
)
