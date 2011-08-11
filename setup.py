# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.txt', 'r') as readme:
    long_description = readme.read()

requires = ['Sphinx>=0.6']

setup(
    name='phix',
    packages=['phix'],
    version='0.5',
    url='http://code.google.com/p/phix/',
    download_url='http://pypi.python.org/pypi/phix',
    license='BSD',
    author='Robert Smallshire',
    author_email='robert@smallshire.org.uk',
    description='Sphinx "phix" extension',
    long_description=long_description,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Documentation',
        'Topic :: Utilities',
    ],
    platforms='any',
    #packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
)