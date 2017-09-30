#!/usr/bin/env python
# -*- coding: utf-8 -*-
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# the most part of this code is used on the quizes
# I did a little modification to deal with the 
# lacking of 'user' problem in teh dataset I have 
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 


# importing
import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET
import cerberus
import schema

# set file path
OSM_PATH = "saint-louis_missouri.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


# This is the function in the quiz
def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    # if we are dealing with 'node' type
    if element.tag == 'node':
        node_id = element.attrib['id']
        # turns out some of the nodes do not have a 'user' attrbute
        # if so, ignore them
        if 'user' not in element.attrib:
            return 
        for each_node_field in node_attr_fields:
            node_attribs[each_node_field] = element.attrib[each_node_field]
        for each_tag in element:
            if each_tag.tag == 'tag':
                temp_dict = {}
                temp_dict['id'] = node_id
                temp_dict['value'] = each_tag.attrib['v']
                # if there is : in the key
                if re.search(LOWER_COLON, each_tag.attrib['k']) != None:
                    temp_dict['type'] = each_tag.attrib['k'][ : each_tag.attrib['k'].index(':')]
                    temp_dict['key'] = each_tag.attrib['k'][each_tag.attrib['k'].index(':') + 1:]
                else:
                    temp_dict['type'] = 'regular'
                    temp_dict['key'] = each_tag.attrib['k']
                tags.append(temp_dict)

    # if we are dealing with 'way' type
    elif element.tag == 'way':
        way_id = element.attrib['id']
        for each_way_field in way_attr_fields:
            way_attribs[each_way_field] = element.attrib[each_way_field]
            ii_nd = 0
        for each_tag in element:
            if each_tag.tag == 'nd':
                temp_dict = {}
                temp_dict['id'] = way_id
                temp_dict['node_id'] = each_tag.attrib['ref']
                temp_dict['position'] = ii_nd
                ii_nd += 1
                way_nodes.append(temp_dict)
            if each_tag.tag == 'tag':
                temp_dict = {}
                temp_dict['id'] = way_id
                temp_dict['value'] = each_tag.attrib['v']
                if re.search(LOWER_COLON, each_tag.attrib['k']) != None:
                    temp_dict['type'] = each_tag.attrib['k'][ : each_tag.attrib['k'].index(':')]
                    temp_dict['key'] = each_tag.attrib['k'][each_tag.attrib['k'].index(':') + 1:]
                else:
                    temp_dict['type'] = 'regular'
                    temp_dict['key'] = each_tag.attrib['k']
                tags.append(temp_dict)
    
    if element.tag == 'node':
        return {'node': node_attribs, 'node_tags': tags}
    elif element.tag == 'way':
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# clean the abbreviation in the 'name_type' value
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

import pandas as pd
# read the csv file
ways_tags_df = pd.read_csv('ways_tags.csv')
# get the unique id list for cleansing
ids = list(ways_tags_df['id'].unique())

# for each id in the whole csv file
for each_id in ids:
    # get all content under this id
    temp_frame_each_id = ways_tags_df.query(''' id == %d ''' % each_id)
    # if there is a 'name' key under this id
    if 'name' in list(temp_frame_each_id['key']) and 'name_type' in list(temp_frame_each_id['key']):
        # get the last word of the value whose key is 'name'
        # from observing, that would be the full type name of this way, like 'Street', 'Avenue'
        # instead of 'st', 'ave'
        way_type_full = temp_frame_each_id.query(''' key == 'name' ''')['value'].values[0].split()[-1]
        # get the index of the 'name_type' which is under the same id
        name_type_index = temp_frame_each_id[temp_frame_each_id['key'] == 'name_type'].index[0]
        # update the value of it using the index we get
        ways_tags_df.loc[name_type_index, 'value'] = way_type_full





if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=True)

