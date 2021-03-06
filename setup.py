# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: CC0-1.0

import setuptools

with open("README.md") as readme:
    long_description = readme.read()

setuptools.setup(
    name="pylab",
    version="0.7.0",
    author="M. Kliemann",
    author_email="mail@maltekliemann.com",
    description="Abstraction layer for hardware test software",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="GPL v3.0",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    entry_points={"console_scripts": ["pylab-cli = pylab._commandline:main"]},
    include_package_data=True,
    classifiers=[
        "Development Status :: 1",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
