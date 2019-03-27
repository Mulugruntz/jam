import os.path


__version__ = 'UNKNOWN'
here = os.path.abspath(os.path.dirname(__file__))
version_file = os.path.join(here, '..', 'version.py')
exec(compile(open(version_file).read(), version_file, 'exec'))
