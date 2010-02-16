from distutils.core import setup
from coil import __version__ as VERSION

setup(
    name = 'coil',
    version = VERSION,
    author = 'Michael Marineau',
    author_email = 'mike@marineau.org',
    description = 'A powerful configuration language',
    license = 'MIT',
    packages = ['coil', 'coil.test'],
    package_data={"coil.test":["*.coil"]},
    scripts = ['bin/coildump'],
    )
