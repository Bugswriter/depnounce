from setuptools import setup
import pathlib

def parse_requirements(filename):
    with open(filename, 'r') as file:
        return [line.strip() for line in file if line.strip() and not line.startswith('#')]

requirements = parse_requirements('requirements.txt')

setup(
    name='depnounce',
    version='0.1',
    py_modules=['main'],
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'depnounce=main:main',
        ],
    },
)
