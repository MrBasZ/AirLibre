from setuptools import setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name = 'AirLibre',
    py_modules = ['AirLibre'],
    install_requires = required,
    version = '0.0.2',
    description = 'UBNT Config API',
    author = 'Nathan Shimp',
    author_email = 'johnnshimp@gmail.com',
    classifiers = [
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'License :: Apache 2',
        'Operating System :: OS Independent',
        'Development Status :: Pre-Alpha',
        'Topic :: Utilities'
    ]
)
