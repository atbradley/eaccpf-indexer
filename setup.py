"""
This file is subject to the terms and conditions defined in the
LICENSE file, which is part of this source code package.
"""

from setuptools import setup, find_packages

setup(name='Indexer',
      description="""A utility for indexing EAC-CPF and related content from a
      web site or file system, inferring data, post-processing and posting
      that data to an Apache Solr search index.""",
      author='(Davis Marques, Marco LaRosa) eScholarship Research Center, University of Melbourne',
      url='http://www.esrc.unimelb.edu.au',
      version='0.1',
      packages=find_packages(),
      install_requires=['beautifulsoup','lxml','pairtree','pyyaml','simplejson'],
)