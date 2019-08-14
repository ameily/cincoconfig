import os
from setuptools import setup

from cincoconfig.version import __version__


def load_requirements(filename):
    path = os.path.join(os.path.dirname(__file__), 'requirements', filename)
    return [line for line in open(path, 'r').readlines()
            if line.strip() and not line.startswith('#')]


requirements = load_requirements('requirements.txt')
dev_requirements = load_requirements('requirements-dev.txt')
feature_requirements = load_requirements('requirements-features.txt')

setup(
    name='cincoconfig',
    version=__version__,
    license='ISC',
    description='Universal configuration file parser',
    long_description=open("README.md", 'r').read(),
    long_description_content_type='text/markdown',
    author='Adam Meily',
    author_email='meily.adam@gmail.com',
    url='https://cincoconfig.readthedocs.io/en/latest/',
    packages=['cincoconfig', 'cincoconfig.formats'],
    install_requires=requirements,
    extras_require={
        'dev': dev_requirements,
        'features': feature_requirements
    },
    project_urls={
        'Travis CI': 'https://travis-ci.org/ameily/cincoconfig',
        'Documentation': 'https://cincoconfig.readthedocs.io/en/latest/',
        'Source': 'https://github.com/ameily/cincoconfig/',
    },
    keywords=['config', 'configuration'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Application Frameworks'
    ]
)
