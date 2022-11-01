from setuptools import setup
import os
from collections import OrderedDict

try:
    long_description = ""
    with open('README.md', encoding='utf-8') as f:
        long_description = f.read()

except:
    print('Curr dir:', os.getcwd())
    long_description = open('../../README.md').read()

setup(name='pyWikiCMS',
      version='0.2.0',
      description='python implementation of a Mediawiki based Content Management System',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/BITPlan/pyWikiCMS',
      download_url='https://github.com/BITPlan/pyWikiCMS',
      author='Wolfgang Fahl',
      author_email='wf@bitplan.com',
      license='Apache',
      project_urls=OrderedDict(
        (
            ("Documentation", "http://wiki.bitplan.com/index.php/PyWikiCMS"),
            ("Code", "https://github.com/BITPlan/pyWikiCMS"),
            ("Issue tracker", "https://github.com/BITPlan/pyWikiCMS/issues"),
        )
      ),
      classifiers=[
            'Programming Language :: Python',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10'
      ],
      packages=['frontend'],
      package_data={
          'templates': ['*.html'],
      },
      install_requires=[
          'lxml',
          'pyFlaskBootstrap4~=0.5.1',
          'py-3rdparty-mediawiki~=0.6.3',
	      'pydevd',
          'beautifulsoup4'
      ],
      zip_safe=False)
