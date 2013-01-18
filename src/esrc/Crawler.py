'''
This file is subject to the terms and conditions defined in the
LICENSE file, which is part of this source code package.
'''

from BeautifulSoup import BeautifulSoup 
import fnmatch
import logging
import os
import time
import urllib2
        
class Crawler(object):
    '''
    File system and web site crawler. Locates EAC metadata files either 
    directly or when specified as an alternate representation to an HTML file. 
    Downloads a copy of the discovered files to a local file system cache for 
    future processing.
    '''

    def __init__(self):
        '''
        Initialize the crawler
        '''
        self.logger = logging.getLogger('feeder')
    
    def _clearFiles(self, path):
        '''
        Delete all files within the specified path.
        '''
        files = os.listdir(path)
        for filename in files:
            os.remove(path + os.sep + filename)
    
    def _getEACSource(self, html):
        '''
        Extract EAC value from HTML meta tag. Return None if nothing found.
        '''
        soup = BeautifulSoup(html)
        meta = soup.findAll('meta', {'name':'EAC'})
        try:
            return meta[0].get('content')
        except:
            return None
    
    def _getFileName(self, url):
        '''
        Get the filename portion of a URL. If no filename is present within the 
        URL, return None. 
        '''
        last = (url.split('/')[-1])
        if (last):
            return last
        return None
    
    def _getHTMLReferrer(self, html):
        '''
        Extract DC.Identifier value from HTML meta tag. Return None if nothing 
        found.
        '''
        soup = BeautifulSoup(html)
        meta = soup.findAll('meta', {'name':'DC.Identifier'})
        try:
            return meta[0].get('content')
        except:
            return None
    
    def _isHTML(self, filename):
        '''
        Determine if a file is an *.htm or *.html file.
        '''
        if fnmatch.fnmatch(filename,'*.html') or fnmatch.fnmatch(filename,'*.htm'):
            return True
        return False
    
    def _isUrl(self, uri):
        ''' 
        Determine if URI is a URL.
        '''
        if 'http://' in uri:
            return True
        return False

    def _makeCache(self, path):
        '''
        Create a cache folder at the specified path if none exists.
        If the path already exists, delete all files.
        '''
        if not os.path.exists(path):
            os.makedirs(path)
            self.logger.info("Created output folder at " + path)
        else:
            self._clearFiles(path)
            self.logger.info("Cleared output folder at " + path)
    
    def crawlFileSystem(self, source='.', output='output', report=None, sleep=0.):
        '''
        Crawl file system for HTML files, starting from the file source, and 
        looking for those files which have EAC, EAC-CPF alternate 
        representations. Mirror EAC files to the specified output. If no 
        output is specified, it creates a default local in the current working 
        directory. Sleep for the specified number of seconds after fetching 
        data.
        '''
        # check state
        assert os.path.exists(source), self.logger.warning("Source path does not exist: " + source)
        assert os.path.exists(output), self.logger.warning("Output path does not exist: " + output)
        if report:
            assert os.path.exists(report), self.logger.warning("Report path does not exist: " + report)
        # walk file system and look for html, htm files
        for path, _, files in os.walk(source):
            for filename in files:
                if self._isHTML(filename):
                    self.logger.debug("Found " + path + os.sep + filename)
                    try:
                        # if the file has an EAC alternate representation
                        infile = open((path + os.sep + filename),'r')
                        html = infile.read()
                        infile.close()
                        src = self._getEACSource(html) 
                        if src:
                            self.logger.debug("Found " + src)
                            # record the URL of the referring document
                            ref = self._getHTMLReferrer(html) 
                            # download the EAC file
                            response = urllib2.urlopen(src)
                            eac = response.read()
                            # append source and referrer URLs into a comment at the end of the eac
                            eac += '\n<!-- @source=%(source)s @referrer=%(referrer)s -->' % {"source":src, "referrer":ref}
                            # write eac file to output
                            outfile = self._getFileName(src)
                            if outfile:
                                outfile = open(output + os.sep + outfile,'w')
                                outfile.write(eac)
                                outfile.close()
                                self.logger.info("Stored " + src)
                    except urllib2.HTTPError:
                        self.logger.warning("Could not fetch EAC file " + src)
                    except Exception:
                        self.logger.warning("Could not complete processing for " + filename, exc_info=True)
                    finally:
                        time.sleep(sleep)
    
    def crawlWebSite(self, source='http://localhost', output='data', report=None, sleep=0.):
        '''
        Crawl web site for HTML pages that have EAC, EAC-CPF alternate 
        representations.  When such a page is found, copy the referenced EAC 
        data file to a local cache for processing. If no cache is specified, 
        it creates a local cache in the current working directory. Sleep
        for the specified number of seconds after fetching data.
        '''
        self.logger.critical("Web site crawling not implemented yet")
        
    def run(self, params):
        '''
        Execute crawl operation using specified parameters.
        '''
        # determine the type of crawl operation to be executed
        source = params.get("crawl","input")
        output = params.get("crawl","output")
        report = params.get("crawl","report")
        sleep = float(params.get("crawl","sleep"))
        # create output folders
        self._makeCache(output)
        if not os.path.exists(report):
            os.makedirs(report)
        # start operation if source is specified
        if (self._isUrl(source)):
            self.crawlWebSite(source,output,report,sleep)
        else:
            self.crawlFileSystem(source,output,report,sleep)
