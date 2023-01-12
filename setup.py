from __future__ import absolute_import

from setuptools import setup

setup(
    name="text2jira",
    version='0.0.0',
    author='Pedro Boechat',
    author_email='pboechat@gmail.com',
    package_dir={'': 'src'},
    py_modules=['text2jira'],
    install_requires = [
        "certifi==2017.4.17",
        "chardet==3.0.4",
        "defusedxml==0.5.0",
        "idna==2.5",
        "jira==1.0.10",
        "oauthlib==2.0.2",
        "pbr==3.0.1",
        "python-dateutil==2.6.0",
        "requests==2.20.0",
        "requests-oauthlib==0.8.0",
        "requests-toolbelt==0.8.0",
        "six==1.10.0",
        "urllib3==1.21.1"
    ],
    entry_points = {
        "console_scripts": ['text2jira = text2jira:main']
    }
)