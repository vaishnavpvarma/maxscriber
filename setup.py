"""
MaXScriber v1.0
Setup script for pip-installable CLI tool.
"""

from setuptools import setup, find_packages

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

with open('requirements.txt', encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='maxscriber',
    version='1.0.0',
    description='Intelligent Multi-Pass Medical PDF Extractor',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='vaishnavpvarma',
    url='https://github.com/vaishnavpvarma',
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'maxscriber=maxscriber.cli:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
    ],
)
