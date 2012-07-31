from distutils.core import setup
from bake.packaging import *

setup(
    name='platoon',
    version='1.0.0a1',
    packages=enumerate_packages('platoon'),
    package_data={
        'platoon': ['migrations/env.py', 'migrations/script.py.mako',
            'migrations/versions/*.py'],
    }
)
