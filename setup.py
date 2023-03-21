from setuptools import setup, find_packages

setup(
    name='sitzungsexport',
    version='0.3.3',
    packages=find_packages(),
    install_requires=[
        'Click',
        'requests',
        'Markdown',
        'sentry-sdk==1.14.0',
    ],
    entry_points='''
        [console_scripts]
        sitzungsexport=sitzungsexport.cli:cli
    ''',
)
