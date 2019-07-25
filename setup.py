"""pyramid_sqlassist installation script.
"""
import os
import re

from setuptools import setup

# store version in the init.py
with open(
        os.path.join(
            os.path.dirname(__file__),
            'pyramid_sqlassist', '__init__.py')) as v_file:
    VERSION = re.compile(
        r".*__VERSION__ = '(.*?)'",
        re.S).match(v_file.read()).group(1)

requires = ['SQLAlchemy>=1.2.0',
            'pyramid',
            'six',
            ]
requires_tests = ['pyramid_mako',
                  'pyramid_debugtoolbar',
                  'transaction',
                  'webtest',
                  'zope.sqlalchemy',
                  ]

setup(
    name="pyramid_sqlassist",
    version=VERSION,
    description="Efficiently manage multiple SqlAlchemy connections for Pyramid",
    long_description='Efficiently manage multiple SqlAlchemy connections for Pyramid',
    classifiers=[
        "Intended Audience :: Developers",
        "Framework :: Pyramid",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="web pyramid sqlalchemy",
    packages=['pyramid_sqlassist'],
    author="Jonathan Vanasco",
    author_email="jonathan@findmeon.com",
    url="https://github.com/jvanasco/pyramid_sqlassist",
    license="MIT",
    zip_safe=False,
    install_requires = requires,
    tests_require = requires + requires_tests,
    test_suite="tests",
)
