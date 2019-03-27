import codecs
import os
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


def _strip_comments(l):
    return l.split('#', 1)[0].strip()


def parse_req_file(filename):
    full_path = os.path.join(os.getcwd(), filename)
    return [_strip_comments(req) for req in codecs.open(full_path, 'r', 'utf-8').readlines() if req]


def install_requires():
    return parse_req_file('requirements.txt')


def tests_require():
    return parse_req_file('requirements_test.txt')


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
    download_url='https://github.com/Mulugruntz/jam/tarball/{}'.format(__version__),
    keywords=['jenkins', 'gce', 'google', 'compute', 'engine'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Distributed Computing',
        'Topic :: Utilities',
    ],
    include_package_data=True,
    install_requires=install_requires(),
    tests_require=tests_require(),
    cmdclass={'test': PyTest},
)
