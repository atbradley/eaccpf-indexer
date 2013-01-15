'''
This file is subject to the terms and conditions defined in the
LICENSE file, which is part of this source code package.
'''

from AlchemyAPI import AlchemyAPI
from BeautifulSoup import BeautifulSoup as soup
from geopy import geocoders
from pythoncalais import Calais
import logging
import os
import time
import yaml 

class Facter(object):
    '''
    Takes an EAC record, executes a semantic analysis of the contents and 
    attempts to extract people, places, things, concepts from free text or 
    structured fields.
    '''

    def __init__(self):
        '''
        Initialize class
        '''
        self.logger = logging.getLogger('feeder')

    def _addValueToDictionary(self,dic,key,value):
        '''
        For dictionaries that hold multiple values for each key.
        '''
        if not dic.has_key(key):
            dic[key] = []
        items = dic[key]
        items.append(value)

    def _cleanList(self, alist):
        '''
        Fix yaml encoding issues for list items.
        '''
        for item in alist:
            item = self._cleanText(item)
        return list

    def _cleanText(self, val):
        '''
        Fix yaml encoding issues for string items.
        '''
        if val == None:
            return ''
        clean = str(val)
        clean = clean.strip()
        # clean = clean.replace('\n','')
        return clean
    
    def _getFreeTextFields(self, xml):
        '''
        Get content from free text fields.
        '''
        freetext = ''
        # /eac-cpf/identity/nameEntry/part
        nameentry = xml.find('nameentry')
        if nameentry:
            parts = nameentry.findAll('part')
            if parts:
                for p in parts:
                    freetext += self._cleanText(p.getString())
        # /eac-cpf/description/biogHist/abstract
        # /eac-cpf/description/biogHist/p
        bioghist = xml.find('bioghist')
        if bioghist:
            abstract = bioghist.find('abstract')
            if abstract:
                freetext += self._cleanText(abstract.getText())
            ps = bioghist.findAll('p')
            if ps:
                for p in ps:
                    freetext += self._cleanText(p.getString())
        # /eac-cpf/description/function/descNote/p
        function = xml.find('function')
        if function:
            functions = function.findAll('p')
            if functions:
                for f in functions:
                    freetext += self._cleanText(f.getString())
        # return
        return freetext

    def _getRecord(self, path, filename):
        '''
        Try to load the entity record. If it does not already exist, return a
        default dictionary record structure. The record is encoded in YAML 
        format.
        '''
        if os.path.exists(path + os.sep + filename):
            # load the existing record file as yaml  
            infile = open(path + os.sep + filename, 'r')
            record = yaml.load(infile)
            infile.close()
            return record
        else:
            # create a default record structure and return it
            return {'comment':'Inferred entity and location data extracted from ' + filename}
        
    def _getResultAsDictionary(self, result):
        '''
        Get Calais result as a dictionary.
        '''
        out = {}
        # entities
        try:
            for e in result.entities:
                entity = {}
                #entity['typeReference'] = self._cleanText(e['_typeReference'])
                entity['type'] = self._cleanText(e['_type'])
                entity['name'] = self._cleanText(e['name'])
                self._addValueToDictionary(out, "entities", entity)
        except:
            pass
        # relations
        try:
            for r in result.relations:
                relation = {}
                #relation['typeReference'] = self._cleanText(r['_typeReference'])
                relation['type'] = self._cleanText(r['_type'])
                self._addValueToDictionary(out, "relations", relation)
        except:
            pass
        # topics
        try:
            for t in result.topics:
                top = {}
                #top['category'] = self._cleanText(t['category'])
                top['categoryName'] = self._cleanText(t['categoryName'])
                self._addValueToDictionary(out, "topics", top)
        except:
            pass
        return out
    
    def _getYamlFilename(self, filename):
        '''
        Takes a file name and returns a name with .yml appended.
        '''
        name, _ = os.path.splitext(filename)
        return name + ".yml"
        
    def _makeCache(self, path):
        '''
        Create a cache folder at the specified path if none exists.
        If the path already exists, delete all files.
        '''
        if not os.path.exists(path):
            os.makedirs(path)
            self.logger.info("Created output folder at " + path)
        else:
            files = os.listdir(path)
            for afile in files:
                os.remove(path + os.sep + afile)
            self.logger.info("Cleared output folder at " + path)
    
    def inferEntitiesWithAlchemy(self, source, output, report, api_key, sleep=0.):
        '''
        For each input file, attempt to extract people, things, concepts and 
        place names from free text fields. Sleep for the specified number of 
        seconds between requests.
        '''
        # Create an AlchemyAPI object, load API key
        alchemy = AlchemyAPI.AlchemyAPI() 
        alchemy.setAPIKey(api_key)
        # check state
        assert os.path.exists(source), self.logger.warning("Specified path does not exist: " + source)
        # process files
        files = os.listdir(source)
        for filename in files:
            # read source data
            infile = open(source + os.sep + filename, 'r')
            lines = infile.readlines()
            xml = soup(''.join(lines))
            infile.close()
            # get the output record
            yamlFilename = self._getYamlFilename(filename)
            record = self._getRecord(output,yamlFilename)
            # clear the existing entities section before populating
            record['inferred_alchemy'] = []
            # get the free text fields from the record
            freetext = self._getFreeTextFields(xml)
            # extract a ranked list of named entities
            result = alchemy.TextGetRankedNamedEntities(freetext);
            self.logger.info(result)
            # record['entities'] = result
            # write output record
            outfile = open(output + os.sep + yamlFilename, 'w')
            yaml.dump(record,outfile)
            outfile.close()
            self.logger.info("Wrote inferred entities to " + yamlFilename)
            # sleep between requests
            time.sleep(sleep)
        
    def inferEntitiesWithCalais(self, source, output, report, api_key, sleep=0.):
        # create an OpenCalais object, load API key
        calais = Calais.Calais(api_key, submitter="University of Melbourne, eScholarship Research Centre")
        #calais.user_directives["allowDistribution"] = "false"
        # check state
        assert os.path.exists(source), self.logger.warning("Specified path does not exist: " + source)
        # process files
        files = os.listdir(source)
        for filename in files:
            # read source data
            infile = open(source + os.sep + filename, 'r')
            lines = infile.readlines()
            xml = soup(''.join(lines))
            infile.close()
            # get the output record
            yamlFilename = self._getYamlFilename(filename)
            record = self._getRecord(output,yamlFilename)
            # clear the existing entities section before populating
            # get free text fields from the record
            freetext = self._getFreeTextFields(xml)
            try:
                # extract entities
                result = calais.analyze(freetext)
                record['inferred_calais'] = self._getResultAsDictionary(result)
                # write output record
                outfile = open(output + os.sep + yamlFilename, 'w')
                yaml.dump(record,outfile)
                outfile.close()
                self.logger.info("Wrote inferred entities to " + yamlFilename)
            except Exception:
                self.logger.warning("Could not complete inference operation for " + filename, exc_info=True)
            # sleep between requests
            time.sleep(sleep)
    
    def inferEntitiesWithNLTK(self, source, output, report):
        '''
        Infer entities from free text using Natural Language Toolkit.
        Attempt to identify people and things.
        '''
        # create output folder
        self._makeCache(output)
        # check state
        assert os.path.exists(source), self.logger.warning("Specified path does not exist: " + source)
        # process files
        files = os.listdir(source)
        for filename in files:
            # read source data
            infile = open(source + os.sep + filename, 'r')
            lines = infile.readlines()
            xml = soup(''.join(lines))
            infile.close()
            # get the output record
            yamlFilename = self._getYamlFilename(filename)
            record = self._getRecord(output,yamlFilename)
            # clear the existing entities section before populating
            record['inferred_nltk'] = []
            # get the free text fields from the record
            freetext = self._getFreeTextFields(xml)
            self.logger.info(freetext)
            # infer entities
            # write output record
            outfile = open(output + os.sep + yamlFilename, 'w')
            yaml.dump(record,outfile)
            outfile.close()
            self.logger.info("Wrote inferred entities to " + yamlFilename)
        
    def inferLocations(self, source, output, report, geocoder, api_key, sleep=0.):
        '''
        For each input file, extract the locationName name or address and 
        attempt to resolve its geographic coordinates. Sleep for the 
        specified number of seconds between requests.
        '''
        # check state
        assert os.path.exists(source), self.logger.warning("Specified path does not exist: " + source)
        # process files
        files = os.listdir(source)
        for filename in files:
            # read source data
            infile = open(source + os.sep + filename, 'r')
            lines = infile.readlines()
            xml = soup(''.join(lines))
            infile.close()
            # get the output record
            yamlFilename = self._getYamlFilename(filename)
            record = self._getRecord(output,yamlFilename)
            # clear the existing locations section before populating
            record['locations'] = []
            # for each chronItem
            for chronItem in xml.findAll('chronitem'):
                try:
                    if 'GIS' in chronItem.place.attrs:
                        # populate the record with the existing GIS data
                        self.logger.warning("Section not implemented")
                    else:
                        # try to resolve the location
                        locationName, coordinates = geocoder.geocode(chronItem.place.string)
                        # if we got data back
                        if locationName and coordinates:
                            location = {}
                            location['date']  = self._cleanText(chronItem.date.string)
                            location['event'] = self._cleanText(chronItem.event.string)
                            location['place'] = self._cleanText(chronItem.place.string)
                            location['address'] = self._cleanText(locationName)
                            location['coordinates'] = [coordinates[0], coordinates[1]]
                            record['locations'].append(location)
                except Exception:
                    self.logger.warning("Could not resolve location record for " + filename, exc_info=True)
            # write output record
            outfile = open(output + os.sep + yamlFilename, 'w')
            yaml.dump(record,outfile)
            outfile.close()
            self.logger.info("Wrote inferred locations to " + yamlFilename)
            # sleep between requests
            time.sleep(sleep)

    def run(self, params):
        '''
        Execute semantic analysis and information extraction using the 
        specified parameters.
        '''
        self.logger.info("Starting inference operation")
        # get parameters
        source = params.get("infer","input")
        output = params.get("infer","output")
        report = params.get("infer","report")
        sleep = float(params.get("infer","sleep"))
        # create output folder
        self._makeCache(output)
        # infer location
        google_api_key = params.get("infer","google_api_key")
        geocoder = geocoders.Google(domain='maps.google.com.au')
        self.inferLocations(source,output,report,geocoder,google_api_key,sleep)
        # infer entities with Alchemy
        #alchemy_api_key = params.get("infer","alchemy_api_key")
        #self.inferEntitiesWithAlchemy(source,output,report,alchemy_api_key,sleep)
        # infer entities with NLTK
        # self.inferEntitiesWithNLTK(source, output, report)
        # infer entities with Open Calais
        calais_api_key = params.get("infer","calais_api_key")
        self.inferEntitiesWithCalais(source,output,report,calais_api_key,sleep)

    