from setuptools import setup, find_packages

setup(
    name='EZPB',
    version='0.0',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        '': ['*.ini', 'tracecomp', 'pb_mpi']
    },
    install_requires=[
        'Click'
    ],
    entry_points='''
        [console_scripts]
        ezpb=ezpb:main
    '''
)
