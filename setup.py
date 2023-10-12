from setuptools import setup

# read the contents of your README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='smatchpp',
    version='1.3.2',    
    description='A Python package for graph processing',
    url='https://github.com/flipz357/smatchpp',
    author='Juri Opitz',
    author_email='opitz.sci@gmail.com',
    license='GPLv3',
    packages=['smatchpp'],
    long_description=long_description,
    long_description_content_type='text/markdown',
    python_requires=">=3.5",
    classifiers=["License :: OSI Approved :: GNU General Public License v3 (GPLv3)"],
    package_data={'smatchpp': ['resource/*']})
