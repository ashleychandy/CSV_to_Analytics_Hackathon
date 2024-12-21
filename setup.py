from setuptools import setup, find_packages

setup(
    name="pos-revenue",
    version="0.1",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'pos=src.cli:app',
        ],
    },
) 