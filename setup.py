import os
from setuptools import setup

from cincoconfig.version import __version__


def load_requirements(filename):
    path = os.path.join(os.path.dirname(__file__), 'requirements', filename)
    return [line for line in open(path, 'r').readlines() if line.strip() and not line.startswith('#')]


requirements = load_requirements('requirements.txt')
dev_requirements = load_requirements('requirements-dev.txt')

setup(
    name='cincoconfig',
    version=__version__,
    license='ISC',
    description='Universal configuration file parser',
    long_description=open("README.md", 'r').read(),
    author='Adam Meily',
    author_email='meily.adam@gmail.com',
    url='https://github.com/ameily/cincoconfig',
    download_url=None,  # TODO
    packages=['cincoconfig', 'cincoconfig.formats', 'cincoconfig.fields'],
    install_requires=requirements,
    extras_require={
        'dev': dev_requirements
    },
    keywords=['config', 'configuration'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Application Frameworks'
    ]
)
