from setuptools import setup

setup(
    name='Phyl-o-Matic',
    version='0.0',
    py_modules=['phylomatic'],
    install_requires=[
        'Click'
    ],
    entry_points='''
        [console_scripts]
        phylomatic=phylomatic:cli
    '''
)
