# -*- coding: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name="ella",
    version="0.0.8",
    description="Elliptics Admin",
    long_description="Web Admin for elliptics storage",
    url="https://github.com/Inkvi/ella",
    author="Anton Tyurin & Alexander Eliseev",
    author_email="noxiouz@yandex.ru",
    license="BSD 2-Clause",
    platforms=["Linux", "BSD", "MacOS"],
    packages=["ella"],
    scripts=['ella-admin'],
    package_data={'ella': ['templates/*', 'static/style.css', 'static/bootstrap/css/*', 'static/bootstrap/js/*',
                           'static/bootstrap/img/*']},
    data_files = [('/etc/ubic/service', ['scripts/ella'])],
    requires=[]
)
