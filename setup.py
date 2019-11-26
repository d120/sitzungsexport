from setuptools import setup, find_packages

setup(
    name='sitzungsexport',
    version='0.2.2',
    packages=find_packages(),
    install_requires=[
        'Click',
        'requests',
        'Markdown',
        'sentry-sdk==0.13.3',
    ],
    entry_points='''
        [console_scripts]
        sitzungsexport=sitzungsexport.cli:cli
    ''',
)
