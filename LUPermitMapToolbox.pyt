"""
File name:      LUPermitMapToolbox.pyt
Description:    This Python toolbox includes tools for the automated generation of PDF maps associated with PDS Land Use
                project information, which is tracked in AMANDA. This toolbox is based on the
Author:         Jesse Langdon, Principal GIS Analyst
Department:     Snohomish County Planning and Development Services (PDS)
Last Update:    1/10/2024
Requirements:   ArcGIS Pro 3.x, Python 3, arcpy
"""

# -*- coding: utf-8 -*-

import os
import arcpy


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Land Use Permit Map Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [GenerateLUMapTool]


class GenerateLUMapTool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Generate Land Use Permit Maps"
        self.description = "This tool generates two new PDF maps for a specific Land Use Permit, which are intended as " \
                            "attachments to be included with the associated AMANDA project folder."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # First parameter
        param0 = arcpy.Parameter(
            displayName="Project Name",
            name="project_name",
            datatype="DEString",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="PFN",
            name="pfn_id",
            datatype="DEString",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Project Manager",
            name="project_manager",
            datatype="DEString",
            parameterType="Required",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="Property ID",
            name="property_id",
            datatype="DEString",
            parameterType="Required",
            direction="Input")

        param4 = arcpy.Parameter(
            displayName="Carto Code",
            name="carto_code",
            datatype="DEString",
            parameterType="Required",
            direction="Input")

        param5 - arcpy.Parameter(
            displayName="Project Year",
            name="project_year",
            datatype="DEString",
            parameterType="Required",
            direction="Input")
        param5.filter.type = "ValueList"
        param5.filter.list = [2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014, 2013, 2012]

        params = [param0, param1, param2, param3, param4, param5]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""


        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


# Helper functions


# Check that the APRX file exists
def check_aprx_file(input_aprx_filepath):
    """
    Checks if the specified APRX file exists in the directory. If not, an error is raised using arcpy.AddError.

    :param aprx_path: Path to the APRX file.
    """
    if not os.path.exists(input_aprx_filepath):
        error_msg = f"APRX file not found: {input_aprx_filepath}"
        arcpy.AddError(error_msg)
        raise FileNotFoundError(error_msg)
    else:
        arcpy.AddMessage(f"APRX file found: {input_aprx_filepath}")
    return


# Iterate through relevant maps and layouts and:
#       generate a list of map objects
#       build a list of layout objects
def list_map_objects(aprx_path, prefix="Map_*"):
    """
    Lists map objects in the APRX file that have a specific prefix in their name.

    :param aprx_path: Path to the APRX file.
    :param prefix: The prefix to search for in map names.
    :return: List of map names with the specified prefix.
    """
    aprx = arcpy.mp.ArcGISProject(aprx_path)
    map_list = [m for m in aprx.listMaps(prefix)] #if m.name.startswith(prefix)
    return map_list


def list_layout_objects(aprx_path):
    """
    Lists all layout objects in the APRX file.

    :param aprx_path: Path to the APRX file.
    :return: List of layout objects.
    """
    aprx = arcpy.mp.ArcGISProject(aprx_path)
    layout_list = aprx.listLayouts()
    return layout_list


# Build list of sanitized tax account IDs from list or tuple of user-supplied parcel IDs
def convert_to_list(input_string):
    """
    Converts a string of values separated by commas or spaces into a list
    :param input_string: string containing values separated by comma or space
    :return: list of values
    """
    value_list = input_string.replace(',', ' ' ).split()
    return value_list


def sanitize_parcel_id(input_parcel_ids):
    """
    Consumes tax account (parcel) IDs and sanitized them by stripping whitespace and "_" characters

    :param input_parcel_id: parcel ID in string format
    :return: list of sanitized parcel ID strings
    """
    list_parcel_ids = convert_to_list(input_parcel_ids)
    sanitized_parcel_ids = [str(parcel_id).strip().replace("-","") for parcel_id in list_parcel_ids]
    return sanitized_parcel_ids


# Build definition query for the Subject Property layer based on found tax ID list
def generate_subject_property_query(list_parcel_ids, field_name="PARCEL_ID"):
    """
    Builds a query from a list of tax account (i.e. parcel) ID values

    :param list_parcel_ids: list of parcel ID values
    :param field_name: name of the attribute field to include in query
    :return: query string
    """
    parcel_id_string = ', '.join(["'{}'".format(value) for value in list_parcel_ids])
    query_string = f"{field_name} IN ({parcel_id_string})"
    arcpy.AddMessage("Query string to select subject property features generated...")
    return query_string


def find_layer(input_map_obj_list, map_name, layer_name):
    """
    Finds a layer object based on wildcard layer name from first map object in the list.

    :param input_map_list: list of map objects
    :param layer_name: wildcard string for the layer name
    :return:  The layer object if found, otherwise None
    """
    try:
        map_obj = next((map for map in input_map_obj_list if map.name == map_name))
        if not map_obj:
            arcpy.AddError(f"Map '{map_name}' not found.")
            return None

        layer_obj = map_obj.listLayers(layer_name)
        arcpy.AddMessage(f"Layer {layer_name} was found in {map_name}...")
        if not layer_obj:
            arcpy.AddWarning(f"No layers matching '{layer_name} were found!")
            return None
        return layer_obj[0]

    except IndexError:
        arcpy.AddError("List of map objects is empty or invalid!")
        return None
    except Exception as e:
        arcpy.AddError(f"{str(e)}")
        return None


def extract_fc_to_memory(src_layer, query_string, target_lyr=r"memory\selected_features"):
    arcpy.AddMessage(f"Extracting features from {src_layer} to {target_lyr}...")
    arcpy.SelectLayerByAttribute_management(in_layer_or_view=src_layer,
                                            selection_type="NEW_SELECTION",
                                            where_clause=query_string)
    arcpy.CopyFeatures_management(in_features=src_layer, out_feature_class=target_lyr)
    return target_lyr


# Select cadastral parcel features based on the user submitted parcel ID values
def check_fc_exists(input_aprx, target_fc):
    default_gdb = input_aprx.defaultGeodatabase
    target_fc_path = os.path.join(default_gdb, target_fc)
    if arcpy.Exists(target_fc_path):
        arcpy.AddMessage(f"{target_fc} found in default geodatabase...")
        return target_fc_path
    else:
        arcpy.AddError(f"Feature class {target_fc} not found in default geodatabase!")


def delete_all_features_in_fc(target_fc_path):
    try:
        arcpy.DeleteRows_management(target_fc_path)
        arcpy.AddMessage(f"Existing feature deleted from {target_fc_path}...")
    except Exception as e:
        arcpy.AddError(f"Error: {str(e)}")
    return


def empty_and_append(input_layer, input_target_fc):
    """
    Select features from a layer and append them to an existing target feature class after emptying the target feature
    class of all features.

    :param input_layer:
    :param input_target_fc:
    :return:
    """
    delete_all_features_in_fc(input_target_fc)
    arcpy.Append_management(inputs=input_layer, target=input_target_fc)
    arcpy.SelectLayerByAttribute_management(in_layer_or_view=input_layer,
                                            selection_type="CLEAR_SELECTION")
    return


def update_fc_data_source_in_maps(list_maps, target_layer_name, data_source_string):
    """
    Iterates through a list of map objects and finds the target layer by name, then updates the data source of that layer
    :param list_maps:
    :param target_layer_name:
    :param data_source_string:
    :return:
    """
    for map in list_maps:
            target_layer = find_layer(list_maps, map.name, target_layer_name)
            try:
                original_conn_prop = target_layer.connectionProperties
                target_layer.updateConnectionProperties(current_connection_info=original_conn_prop,
                                                        new_connection_info=data_source_string)
                arcpy.AddMessage(f"Updated data source for layer {target_layer} in {map.name}...")
                return target_layer
            except Exception as e:
                arcpy.AddError(f"Failed to update data source for layer {target_layer_name} in {map.name}. Error: {e}")



# Create a safe version of the PFN
def sanitize_pfn (pfn_id):

    return


# TESTING
param0 = "Manvar Plat"
param1 = "2023 119498 000 00 SHOR" # pfn_id
param2 = "Kim Mason-Hatt"
param3 = "003741-001-014-01, 003741-001-013-00"
param4 = "carto_code"
param5 = "2023"

params = [param0, param1, param2, param3, param4, param5]
aprx_filepath = r"C:\Users\SCDJ2L\dev\LUPermitToolbox\PermitMaps_TEST.aprx"

# Open required objects from APRX file
check_aprx_file(aprx_filepath)
aprx_obj = arcpy.mp.ArcGISProject(aprx_filepath)
list_map_obj = list_map_objects(aprx_filepath)
list_layout_obj = list_layout_objects(aprx_filepath)
list_parcel_ids = sanitize_parcel_id(params[3])
qry_parcel_ids = generate_subject_property_query(list_parcel_ids)

# Find the cadastral parcel layer in the Map_OZMap map object
map_name = "Map_OZMap"
layer_name = "Cadastral Parcel"
found_layer_obj = find_layer(list_map_obj, map_name, layer_name)
if found_layer_obj:
    arcpy.AddMessage(f"Parcel layer found: {found_layer_obj}")
else:
    arcpy.AddWarning(f"Parcel layer not found")

# Extract the subject property parcel features, and dissolve (if number of parcels is > 1)
memory_lyr_extract = extract_fc_to_memory(found_layer_obj, qry_parcel_ids)
memory_lyr = r"memory\memory_lyr"
if len(list_parcel_ids) > 1:
    arcpy.AddMessage("There are > 1 parcels. The parcel boundaries will be dissolved...")
    arcpy.Dissolve_management(in_features=memory_lyr_extract, out_feature_class=memory_lyr)
else:
    arcpy.MakeFeatureLayer_management(in_features=memory_lyr_extract, out_layer=memory_lyr)
target_fc = "SubjectProperty"
target_fc_filepath = check_fc_exists(aprx_obj, target_fc)
empty_and_append(memory_lyr, target_fc_filepath)

# Pan and zoom to extent of subject property feature
subject_prop_lyr_obj = next((map_obj.listLayers("Subject Property")[0]
                             for map_obj in list_map_obj if map_obj.name == "Map_OZMap"), None)
arcpy.MakeFeatureLayer_management(in_features=target_fc_filepath, out_layer="Subject Property")
arcpy.SelectLayerByAttribute_management(in_layer_or_view="Subject Property",selection_type="NEW_SELECTION")
layer_extent_data = arcpy.da.Describe("Subject Property")['extent']
extent_obj = arcpy.Extent(layer_extent_data.XMin, layer_extent_data.YMin, layer_extent_data.XMax, layer_extent_data.YMax)


# Zoom to extent of subject property feature
for lyt in list_layout_obj:
    mapframe_list = lyt.listElements("MAPFRAME_ELEMENT")
    for mf in mapframe_list:
        if mf.map.name in ("Map_OZMap", "Map_Aerial"):
            mf.camera.setExtent(extent_obj)

aprx_obj.saveACopy(r"C:\Users\SCDJ2L\dev\LUPermitToolbox\TEST.aprx")
print("Testing complete")