"""pyramid_sqlassist installation script.
"""
import os
import re

from setuptools import setup
from setuptools import find_packages

HERE = os.path.abspath(os.path.dirname(__file__))

# store version in the init.py
with open(os.path.join(HERE, "src", "pyramid_sqlassist", "__init__.py")) as v_file:
    VERSION = re.compile(r'.*__VERSION__ = "(.*?)"', re.S).match(v_file.read()).group(1)

long_description = (
    description
) = "Efficiently manage multiple SqlAlchemy connections for Pyramid"
with open(os.path.join(HERE, "README.md")) as fp:
    long_description = fp.read()

requires = [
    "SQLAlchemy>1.4.7",
    "pyramid",
    "six",
]
tests_require = [
    "pytest",
    "pyramid_mako",
    "pyramid_debugtoolbar",
    "pyramid_tm",
    "transaction",
    "webtest",
    "zope.sqlalchemy>=1.6",
]
testing_extras = tests_require + []

setup(
    name="pyramid_sqlassist",
    version=VERSION,
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Intended Audience :: Developers",
        "Framework :: Pyramid",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="web Pyramid SQLAlchemy",
    packages=find_packages(
        where="src",
    ),
    package_dir={"": "src"},
    include_package_data=True,
    author="Jonathan Vanasco",
    author_email="jonathan@findmeon.com",
    url="https://github.com/jvanasco/pyramid_sqlassist",
    license="MIT",
    zip_safe=False,
    install_requires=requires,
    tests_require=tests_require,
    extras_require={
        "testing": testing_extras,
    },
    test_suite="tests",
)
