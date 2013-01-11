EAC, EAC-CPF Web Crawler and Data Processing Utility
====================================================

EAC-Crawler is a utility for harvesting EAC, EAC-CPF from a file system or the 
Internet, and post-processing it for applications such as search indexing, and
visualization in maps or timelines. The utility is able to extract concepts, 
people and locations from free text or structured data fields. Inferred data 
is written to disk to enable various usages.


Credits
-------

EAC-Crawler is a project of the eScholarship Research Center at the University 
of Melbourne. For more information about the project, please contact us at:

  eScholarship Research Center
  University of Melbourne
  Parkville, Victoria
  Australia
  www.esrc.unimelb.edu.au

Authors:

 * Davis Marques <davis.marques@unimelb.edu.au>
 * Marco La Rosa <marco@larosa.org.au>
  
Thanks:

 * Alchemy API - http://www.alchemy.com
 * Beautiful Soup - http://www.crummy.com/software/BeautifulSoup
 * Google Maps API - http://maps.google.com
 * NumPy - http://www.numpy.org/
 * Natural Language Toolkit - http://nltk.org
 * Python - http://www.python.org
 * PyYAML - http://pyyaml.org/


License
-------

Please see the LICENSE file for licence information.


Installation
------------

Requires Python 2.7.x


Usage
-----

The crawler is run from the command line. Starting at the seed page or pages, it 
will visit all pages within the seed domain that are linked to that starting 
page. Where an HTML page provides an EAC alternate representation, the crawler 
will fetch, parse and transform the EAC document into a Solr Input Document, 
then insert the record into Solr.  In addition, the crawler can generate a 
report on the quality of the EAC that is indexed.


Revision History
----------------

1.1.3
? Consider fixing broken source HTML, etc. files in place
? Posts Solr Input Documents to Solr core
? Writes processing messages to report log
? Analyzes EAC data for quality indicators
? Merges individual reports into a single report file

1.1.2
? Transforms EAC to Solr Input Document format using an external XSLT file
? Merges inferred data with Solr Input Documents
- Requires update to the Solr index configuration

1.1.1
? Converts place names in structured fields into geographic coordinates for mapping
? Extracts entities (people, places, things, concepts) from free text fields
? Writes inferred data to cache folder

1.1.0
- Revised application architecture
- Reads configuration from file
- Crawls file system for EAC, EAC-CPF files
- Cleans input data to resolve common XML errors

1.0.0
- Initial production release
