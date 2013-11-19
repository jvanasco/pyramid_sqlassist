"""pyramid_sqlassist installation script.
"""
import os

from setuptools import setup
from setuptools import find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, "README.md")).read()
README = README.split("\n\n", 1)[0] + "\n"

requires = ['SQLAlchemy>=0.8.0']

setup(name="pyramid_sqlassist",
      version="0.1.4",
      description="Experimental SqlAlchemy support for Pyramid",
      long_description=README,
      classifiers=[
        "Intended Audience :: Developers",
        "Framework :: Pyramid",
        "Programming Language :: Python",
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
      test_suite="tests",
      )

