import codecs
import pipfile
import setuptools
import setuptools.command.test
import sys


__version__ = 'UNKNOWN'
exec(open('version.py').read())


def long_description():
    try:
        return codecs.open('README.md', 'r', 'utf-8').read()
    except IOError:
        return 'Long description error: Missing README.md file'


def parse_pipfile(package):
    pf = pipfile.load('Pipfile')
    return [f'{pack}{version}' for pack, version in pf.data[package].items()]


def install_requires():
    return parse_pipfile('default')


def tests_require():
    return parse_pipfile('develop')


class PyTest(setuptools.command.test.test):
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        setuptools.command.test.test.initialize_options(self)
        self.pytest_args = ''

    def run_tests(self):
        import shlex
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


setuptools.setup(
    name='jam',
    packages=['jam'],
    version=__version__,
    description='A Jenkins Agent Manager for Google Compute Engine',
    long_description=long_description(),
    author='Samuel GIFFARD',
    author_email='mulugruntz@gmail.com',
    license='MIT',
    url='https://github.com/Mulugruntz/jam',
    download_url=f'https://github.com/Mulugruntz/jam/tarball/{__version__}',
    keywords=['jenkins', 'gce', 'google', 'compute', 'engine'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Distributed Computing',
        'Topic :: Utilities',
    ],
    include_package_data=True,
    install_requires=install_requires(),
    tests_require=tests_require(),
    cmdclass={'test': PyTest},
)
