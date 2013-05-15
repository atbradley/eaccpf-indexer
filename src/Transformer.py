'''
This file is subject to the terms and conditions defined in the
LICENSE file, which is part of this source code package.
'''

from HtmlPage import HtmlPage
from lxml import etree

import inspect
import logging
import os
import re 
import yaml

class Transformer(object):
    '''
    Merge and transform source data to Solr Input Document format.
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.logger = logging.getLogger('Transformer')

    def _escapeChars(self, Text):
        '''
        Escape characters as required for XML output.
        '''
        Text = Text.replace(" & "," &amp; ")
        return Text

    def _getFileName(self, Url):
        '''
        Get the filename from the specified URI or path.
        '''
        if "/" in Url:
            parts = Url.split("/")
            return parts[-1]
        return Url

    def _getIdFromFilename(self,Filename):
        '''
        Get the record ID from the filename.
        '''
        recordId, _ = os.path.splitext(Filename)
        return recordId

    def _getSourceAndReferrerValues(self, Path):
        '''
        Get document source and referrer URI values from the comment embedded 
        at the end of the document.
        '''
        infile = open(Path,'r')
        lines = infile.readlines()
        infile.close()
        # process lines
        for line in lines:
            try:
                src = line.index("@source")
                meta = line.index("@metadata")
                pres = line.index("@presentation")
                source = line[src+len("@source="):meta-1]
                metadata = line[meta+len("@metadata="):pres-1]
                presentation = line[pres+len("@presentation="):-4]
                return (source, metadata, presentation)
            except:
                pass
        # default case
        return ('', '')
    
    def _isDigitalObjectYaml(self, Path):
        '''
        Determines if the file at the specified path is an image record in
        YAML format.
        '''
        if Path.endswith("yml"):
            infile = open(Path,'r')
            data = infile.read()
            infile.close()
            if "cache_id" in data:
                return True
        return False

    def _isInferredYaml(self, Path):
        '''
        Determines if the file at the specified path is an inferred data
        record in YAML format.
        '''
        if Path.endswith("yml"):
            return True
        return False
    
    def _isSolrInputDocument(self, Path):
        '''
        Determines if the file at the specified path is a Solr Input
        Document.
        '''
        if Path.endswith("xml"):
            infile = open(Path,'r')
            data = infile.read()
            infile.close()
            if "<add>" in data and "<doc>" in data:
                return True
        return False

    def _makeCache(self, Path):
        '''
        Create a cache folder at the specified Path if none exists.
        If the Path already exists, delete all files.
        '''
        if not os.path.exists(Path):
            os.makedirs(Path)
            self.logger.info("Created output folder at " + Path)
        else:
            files = os.listdir(Path)
            for afile in files:
                os.remove(Path + os.sep + afile)
            self.logger.info("Cleared output folder at " + Path)

    def _removeNameSpaces(self, Text):
        '''
        Remove namespace references from XML data.
        
        ISSUE #4: When the XML/XSLT parser encounters a problem, it fails 
        silently and does not return any results. We've found that the 
        problem occurs due to namespace declarations in source files. 
        Because these are not important in the transformation to SID 
        format, we strip them out here before processing.
        '''
        for ns in re.findall("\w*:\w*=\".*\"", Text):
            Text = Text.replace(ns,'')
        for ns in re.findall("xmlns=\".*\"", Text):
            Text = Text.replace(ns,'')
        return Text
    
    def mergeDigitalObjectIntoSID(self, Source, Output):
        '''
        Merge the digital object record into the Solr Input Document.
        Do not overwrite existing id, presentation_url and metadata_url fields.        
        '''
        try:
            infile = open(Source,'r')
            data = infile.read()
            dobj = yaml.load(data)
            infile.close()
            filename = self._getFileName(Source).replace('.yml','.xml')
            # if there is an existing SID file, then read it into memory
            if os.path.exists(Output + os.sep + filename):
                parser = etree.XMLParser(remove_blank_text=True)
                xml = etree.parse(Output + os.sep + filename, parser)
                root = xml.getroot()
                doc = root.getchildren()[0]
                # add fields
                for field in dobj.keys():
                    if field.startswith('dobj'):
                        dobjfield = etree.Element("field", name=field)
                        dobjfield.text = dobj[field]
                        doc.append(dobjfield)
                # write the updated file
                outfile = open(Output + os.sep + filename,'w')
                xml.write(outfile, pretty_print=True, xml_declaration=True)
                outfile.close()
                self.logger.info("Merged digital object into " + filename)
        except:
            self.logger.warning("Could not complete merge processing for " + filename, exc_info=True)
    
    def mergeDigitalObjectsIntoSID(self, Sources, Output):
        '''
        Merge digital object records into Solr Input Documents.
        '''
        for source in Sources:
            files = os.listdir(source)
            for filename in files:
                if self._isDigitalObjectYaml(source + os.sep + filename):
                    path = source + os.sep + filename
                    self.mergeDigitalObjectIntoSID(path, Output)
                    
    def mergeInferredRecordIntoSID(self, Source, Output):
        '''
        Merge inferred data into Solr Input Document. Write merged data to 
        output.
        '''
        try:
            # read input (inferred) data file
            infile = open(Source,'r')
            data = infile.read()
            inferred = yaml.load(data)
            infile.close()
            filename = self._getFileName(Output)
            # if there is an existing SID file, then read it into memory, 
            # otherwise create an XML tree to 
            if not os.path.exists(Output):
                root = etree.Element("add")
                xml = etree.ElementTree(root)
                doc = etree.Element("doc")
                root.append(doc)
                # add required records
                recordId = etree.Element("field", name="id")
                recordId.text = self._getIdFromFilename(filename)
                doc.append(recordId)
            else:
                # read output (Solr Input Document) data file
                parser = etree.XMLParser(remove_blank_text=True)
                xml = etree.parse(Output, parser)
                root = xml.getroot()
                doc = root.getchildren()[0]
            # add inferred locations
            # ISSUE #5 the geocoder can return multiple locations when an address is
            # not specific enough. Or, in some cases, a record has multiple events and
            # associated locations.  The Solr index allows for one location field entry, 
            # and multiple geohash entries.  Here, we use the first location as the 
            # primary record location, then make all subsequent locations geohashes.
            if 'locations' in inferred:
                count = 0
                for location in inferred['locations']:
                    # the first location in the list will become the 
                    # primary entity locaion
                    if count == 0:
                        # address
                        address = etree.Element('field', name='address')
                        address.text = location['address']
                        doc.append(address)
                        # city
                        city = etree.Element('field', name='city')
                        city.text = location['city']
                        doc.append(city)
                        # state
                        region = etree.Element('field', name='region')
                        region.text = location['region']
                        doc.append(region)
                        # region
                        country = etree.Element('field', name='country')
                        country.text = location['country']
                        doc.append(country)
                        # coordinates
                        lat = location['coordinates'][0]
                        lng = location['coordinates'][1]
                        latlng = str(lat) + "," + str(lng)
                        coordinates = etree.Element('field', name='location')
                        coordinates.text = latlng
                        doc.append(coordinates)
                        # latitude
                        location_0 = etree.Element('field', name='location_0_coordinate')
                        location_0.text = str(lat)
                        # longitude
                        doc.append(location_0)
                        location_1 = etree.Element('field', name='location_1_coordinate')
                        location_1.text = str(lng)
                        doc.append(location_1)
                    else:
                        # all subsequent locations will be added to the loocation_geohash field
                        lat = location['coordinates'][0]
                        lng = location['coordinates'][1]
                        latlng = str(lat) + "," + str(lng)
                        coordinates = etree.Element('field', name='location_geohash')
                        coordinates.text = latlng
                        doc.append(coordinates)
                    # increment count
                    count = count + 1
                # @todo: add inferred entities
                if 'entities' in inferred:
                    for entity in inferred['entities']:
                        if entity['type'] == 'City':
                            pass
                        elif entity['type'] == 'Concept':
                            pass
                        elif entity['type'] == 'Organization':
                            pass
                        elif entity['type'] == 'Person':
                            pass
                        elif entity['type'] == 'Region':
                            pass
                # @todo: add inferred relationships
                if 'relationship' in inferred:
                    pass
                # @todo: add inferred topics
                if 'topic' in inferred:
                    pass
                # write the updated file
                outfile = open(Output,'w')
                xml.write(outfile, pretty_print=True, xml_declaration=True)
                outfile.close()
                self.logger.info("Merged inferred data into " + filename)
        except Exception:
            self.logger.warning("Could not complete merge processing for " + filename, exc_info=True)
    
    def mergeInferredRecordsIntoSID(self, Sources, Output):
        '''
        Transform zero or more paths with inferred object records to Solr Input 
        Document format.
        '''
        for source in Sources:
            files = os.listdir(source)
            for filename in files:
                if self._isInferredYaml(source + os.sep + filename):
                    outputFileName = self._getIdFromFilename(filename) + ".xml"
                    self.mergeInferredRecordIntoSID(source + os.sep + filename, Output + os.sep + outputFileName)
    
    def run(self, Params):
        '''
        Execute transformations on source documents as specified. Write results 
        to the output path.
        '''
        # get parameters
        actions = Params.get("transform","actions").split(',')
        boosts = Params.get("transform","boost").split(',')
        output = Params.get("transform","output")
        sources = Params.get("transform","inputs").split(",")
        fields = Params.get("transform","set-fields").split(",")
        # check stateWrote
        for source in sources:
            assert os.path.exists(source), self.logger.warning("Source path does not exist: " + source)
        # create output folder
        self._makeCache(output)
        # check state
        assert os.path.exists(output), self.logger.warning("Output path does not exist: " + output)
        # execute actions in order
        if "eaccpf-to-sid" in actions:
            # load schema
            modpath = os.path.abspath(inspect.getfile(self.__class__))
            xslt = os.path.dirname(modpath) + os.sep + "schema" + os.sep + "eaccpf-to-solr.xsl"
            xslt_file = open(xslt,'r')
            xslt_data = xslt_file.read()
            xslt_root = etree.XML(xslt_data)
            xslt_file.close()
            try:
                transform = etree.XSLT(xslt_root)
            except:
                self.logger.critical("Could not load XSLT file " + xslt)    
            self.transformEacCpfsToSID(sources,output,transform)
        if "html-to-sid" in actions:
            self.transformHtmlsToSid(sources,output)
        if 'merge-digitalobjects' in actions:
            self.mergeDigitalObjectsIntoSID(sources,output)
        if "digitalobjects-to-sid" in actions:
            self.transformDigitalObjectsToSID(sources,output)
        if "merge-inferred" in actions:
            self.mergeInferredRecordsIntoSID(sources,output)
        if "set-fields" in actions:
            self.setFieldValue(output,fields)
        # boost fields
        if boosts:
            self.setBoosts(source,boosts)
        # validate output
        try:
            schema = Params.get("transform","schema")
            self.validate(output,schema)
        except:
            self.logger.debug("No schema file specified")
    
    def setBoosts(self, Source, Boosts):
        '''
        Boost the specified field for all Solr Input Documents.
        '''
        assert os.path.exists(Source), self.logger.warning("Source documents path does not exist: " + Source)
        files = os.listdir(Source)
        for filename in files:
            if self._isSolrInputDocument(Source + os.sep + filename):
                try:
                    # parse the document
                    xml = etree.parse(Source + os.sep + filename)
                    for boost in Boosts:
                        fieldname, boostval = boost.split(':')
                        fields = xml.findall('//field[@name="' + fieldname + '"]')
                        for field in fields:
                            # add the boost value
                            field.attrib['boost']=boostval
                    # save the updated document
                    outfile = open(Source + os.sep + filename,'w')
                    data = etree.tostring(xml, pretty_print=True)
                    outfile.write(data)
                    outfile.close()
                    self.logger.info("Applied boosts to " + filename)
                except:
                    self.logger.warning("Could not apply boosts to " + filename)
    
    def setFieldValue(self, Source, FieldValue):
        '''
        Set the specified field value for all Solr Input Documents.
        '''
        assert os.path.exists(Source), self.logger.warning("Source documents path does not exist: " + Source)
        files = os.listdir(Source)
        parser = etree.XMLParser(remove_blank_text=True)
        for filename in files:
            if self._isSolrInputDocument(Source + os.sep + filename):
                try:
                    # load the document
                    xml = etree.parse(Source + os.sep + filename, parser)
                    root = xml.getroot()
                    doc = root.getchildren()[0]
                    # set the field values
                    for fieldvalue in FieldValue:
                        fieldname, value = fieldvalue.split(":")
                        fields = doc.findall('field[@name="' + fieldname + '"]')
                        # if the field exists, change its value
                        if len(fields) > 0:
                            for field in fields:
                                field.text = value
                        else:
                            newfield = etree.Element("field", name=fieldname)
                            newfield.text = value
                            doc.append(newfield)
                    # save the updated document
                    outfile = open(Source + os.sep + filename,'w')
                    data = etree.tostring(xml, pretty_print=True)
                    outfile.write(data)
                    outfile.close()
                    self.logger.info("Set fields in " + filename)
                except:
                    self.logger.warning("Could not set field " + fieldname + " in " + filename)

    def transformDigitalObjectsToSID(self,Sources,Output):
        '''
        Transform zero or more paths with digital object YAML records to Solr 
        Input Document format.
        '''
        for source in Sources:
            files = os.listdir(source)
            for filename in files:
                if self._isDigitalObjectYaml(source + os.sep + filename):
                    path = source + os.sep + filename
                    self.transformDigitalObjectToSID(path,Output)
    
    def transformDigitalObjectToSID(self, Source, Output):
        '''
        Transform a single digital object YAML record to Solr Input Document 
        format.
        '''
        # read input file
        infile = open(Source,'r')
        data = yaml.load(infile.read())
        infile.close()
        # create output data
        xml = "<?xml version='1.0' encoding='ASCII'?>"
        xml += "\n<add>\n\t<doc>"
        for key in data.keys():
            if data[key]:
                xml += "\n\t\t<field name='" + key + "'>" + self._escapeChars(data[key]) + "</field>\n"
        xml += "\n\t</doc>\n</add>"
        # create a new XML Output file
        filename = data['id'] + ".xml"
        outpath = Output + os.sep + filename
        outfile = open(outpath,'w')
        outfile.write(xml)
        outfile.close()
        self.logger.info("Transformed digital object YAML to SID " + filename)
            
    def transformEacCpfsToSID(self, Sources, Output, Transform):
        '''
        Transform zero or more paths containing EAC-CPF documents to Solr Input
        Document format. 
        '''
        for source in Sources:
            files = os.listdir(source)
            for filename in files:
                if filename.endswith(".xml"):
                    self.transformEacCpfToSID(source + os.sep + filename, Output, Transform)
    
    def transformEacCpfToSID(self, Source, Output, Transform):
        '''
        Transform document to Solr Input Document format using the
        specified XSLT transform file.
        '''
        try:
            # read source data
            infile = open(Source,'r')
            data = infile.read()
            infile.close()
            # ISSUE #4: remove namespaces in the XML document before transforming
            data = self._removeNameSpaces(data)
            # create document tree
            xml = etree.XML(data)
            # transform the document
            result = Transform(xml)
            # get the doc element
            sid = result.find('doc')
            # get the document source and referrer values from the embedded comment
            _, meta_val, pres_val = self._getSourceAndReferrerValues(Source)
            # append the source and referrer values to the SID
            if meta_val:
                src_field = etree.Element('field',name='metadata_url')
                src_field.text = meta_val
                sid.append(src_field)
            if pres_val:
                ref_field = etree.Element('field',name='presentation_url')
                ref_field.text = pres_val
                sid.append(ref_field)
            # write the output file
            filename = self._getFileName(Source)
            outfile = open(Output + os.sep + filename, 'w')
            result.write(outfile, pretty_print=True, xml_declaration=True)
            outfile.close()
            self.logger.info("Transformed to Solr Input Document " + filename)
        except Exception:
            self.logger.warning("Could not transform EAC-CPF to Solr Input Document " + filename, exc_info=True)

    def transformHtmlsToSid(self, Sources, Output):
        '''
        Transform HTML documents to Solr Input Document format.
        '''
        for source in Sources:
            files = os.listdir(source)
            for filename in files:
                path = source + os.sep + filename
                html = HtmlPage(path)
                self.transformHtmlToSid(html,Output)

    def transformHtmlToSid(self, Html, Output):
        '''
        Transform HTML to Solr Input Document format.
        '''
        data = Html.getHtmlIndexContent()
        if 'abstract' in data:
            abstract = data['abstract']
        else:
            abstract = ""
        if 'id' in data:
            recordid = data['id']
        else:
            recordid = "unknown"
        if 'title' in data:
            title = data['title']
        else:
            title = ""
        if 'uri' in data:
            uri = data['uri']
        else:
            uri = ""
        outfile_path = Output + os.sep + Html.getRecordId() + ".xml"
        outfile = open(outfile_path,'w')
        outfile.write("<?xml version='1.0' encoding='UTF-8'?>\n")
        outfile.write("<add>\n\t<doc>\n")
        outfile.write("\t\t<field name='abstract'>" + abstract + "</field>\n")
        outfile.write("\t\t<field name='id'>" + recordid + "</field>\n")
        outfile.write("\t\t<field name='title'>" + title + "</field>\n")
        outfile.write("\t\t<field name='source_uri'>" + uri + "</field>\n")
        outfile.write("\t</doc>\n</add>")
        outfile.close()
        self.logger.info("Transformed HTML to SID " + Html.getUrl())

    def validate(self, Source, Schema):
        '''
        Validate a collection of files against an XML schema.
        '''
        # load schemas
        try:
            infile = open(Schema, 'r')
            schema_data = infile.read()
            schema_root = etree.XML(schema_data) 
            schema = etree.XMLSchema(schema_root)
            infile.close()
            self.logger.info("Loaded schema file " + schema)
        except Exception:
            self.logger.critical("Could not load schema file " + schema)
        # create validating parser
        parser = etree.XMLParser(schema=schema)
        # validate files against schema
        files = os.listdir(Source)
        for filename in files:
            infile = open(Source + os.sep + filename,'r')
            data = infile.read()
            infile.close()
            try:
                etree.fromstring(data, parser)
            except Exception:
                self.logger.warning("Document does not conform to schema " + filename)
