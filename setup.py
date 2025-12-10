#!/usr/bin/env python3
"""
Setup script for Website Cloner Pro.

Installs the website_cloner package with all dependencies.
"""

from setuptools import setup, find_packages
import os

# Read the README for long description
here = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(here, 'README.md')

if os.path.exists(readme_path):
    with open(readme_path, 'r', encoding='utf-8') as f:
        long_description = f.read()
else:
    long_description = 'A modern Python-based website cloning and UI extraction tool.'

# Read requirements
requirements_path = os.path.join(here, 'requirements.txt')
install_requires = []
if os.path.exists(requirements_path):
    with open(requirements_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                install_requires.append(line)

setup(
    name='website-cloner',
    version='2.0.0',
    author='Website Cloner Team',
    author_email='',
    description='A modern Python-based website cloning and UI extraction tool',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/hell-webcoder/cloner',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'website_cloner.web': ['templates/*.html', 'static/*.css'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Internet :: WWW/HTTP :: Site Management',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.8',
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'website-cloner=website_cloner.main:run',
            'website-cloner-web=website_cloner.web.run:main',
        ],
    },
    keywords=[
        'website',
        'cloner',
        'scraper',
        'crawler',
        'offline',
        'archive',
        'backup',
        'ui-extraction',
        'screenshot',
    ],
)
