import os.path


__version__ = 'UNKNOWN'
here = os.path.abspath(os.path.dirname(__file__))
execfile(os.path.join(here, '..', 'version.py'))
