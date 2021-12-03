#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages
import shutil
import glob

for file in glob.glob(r'js/dist/*'):
    shutil.copy(file, "ipyshiny/static/")

with open('README.md') as readme_file:
    readme = readme_file.read()

requirements = [ ]

test_requirements = ['pytest>=3', ]

setup(
    author="Carson Sievert",
    author_email='carson@rstudio.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Render ipywidgets inside PyShiny",
    install_requires=requirements,
    license="MIT license",
    long_description=readme,
    include_package_data=True,
    keywords='ipyshiny',
    name='ipyshiny',
    packages=find_packages(include=['ipyshiny', 'ipyshiny.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/rstudio/ipyshiny',
    version='0.1.0',
    zip_safe=False,
)
