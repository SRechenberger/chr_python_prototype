from setuptools import setup

from chr import __version__

setup(
    name='chr-python',
    version=__version__,
    packages=['chr', 'test', 'test_files'],
    url='',
    license='MIT',
    author='Sascha Rechenberger',
    author_email='sascha.rechenberger@uni-ulm.de',
    description='Constraint Handling Rules for Python'
)
