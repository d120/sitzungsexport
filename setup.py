from setuptools import setup, find_packages

setup(
    name='sitzungsexport',
    version='0.3.3',
    packages=find_packages(),
    install_requires=[
        'Click',
        'requests',
        'Markdown',
    ],
    entry_points='''
        [console_scripts]
        sitzungsexport=sitzungsexport.cli:cli
    ''',
)
