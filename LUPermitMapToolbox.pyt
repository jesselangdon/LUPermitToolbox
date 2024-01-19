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
import time # TESTING


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
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # TESTING
        param0.value = "Manvar Plat"

        param1 = arcpy.Parameter(
            displayName="PFN",
            name="pfn_id",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # TESTING
        param1.value = "23 119498"

        param2 = arcpy.Parameter(
            displayName="Project Manager",
            name="project_manager",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # TESTING
        param2.value = "Kim Mason-Hatt"

        param3 = arcpy.Parameter(
            displayName="Property ID",
            name="property_id",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # TESTING
        param3.value = "003741-001-013-00"

        param4 = arcpy.Parameter(
            displayName="Carto Code",
            name="carto_code",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # TESTING
        param4.value = "9999"

        params = [param0, param1, param2, param3, param4]
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

    def execute(self, params, messages):
        """The source code of the tool."""

        # Open required objects from APRX file
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        list_map_obj = list_map_objects(aprx)
        list_layout_obj = list_layout_objects(aprx)
        list_parcel_ids = sanitize_parcel_id(params[3].valueAsText)
        qry_parcel_ids = generate_subject_property_query(list_parcel_ids)

        # Find the cadastral parcel layer in the Map_OZMap map object
        map_name = "Map_OZMap"
        parcel_layer_name = "Cadastral Parcel"
        found_layer_obj = find_layer(list_map_obj, map_name, parcel_layer_name)
        if found_layer_obj:
            arcpy.AddMessage(f"Parcel layer found: {found_layer_obj}")
        else:
            arcpy.AddError(f"Parcel layer not found!")

        # Select the subject property features from the cadastral parcel layer, and dissolve (if number of parcels is > 1)
        memory_lyr_extract = extract_fc_to_memory(found_layer_obj, qry_parcel_ids)
        memory_lyr = r"memory\memory_lyr"
        if len(list_parcel_ids) > 1:
            arcpy.AddMessage("There are > 1 parcels. The parcel boundaries will be dissolved...")
            arcpy.Dissolve_management(in_features=memory_lyr_extract, out_feature_class=memory_lyr)
        else:
            arcpy.MakeFeatureLayer_management(in_features=memory_lyr_extract, out_layer=memory_lyr)

        # Empty the subject property feature class in the project file GDB, and append the selected subject property feature
        arcpy.AddMessage("Emptying the subject property feature class of all features...")
        subject_prop_fc = "SubjectProperty"
        subject_prop_fc_path = check_fc_exists(aprx, subject_prop_fc)
        empty_and_append(memory_lyr, subject_prop_fc_path)
        arcpy.RecalculateFeatureClassExtent_management(subject_prop_fc_path)
        arcpy.Delete_management(memory_lyr)

        # Determine buffer size based on where the subject property is located relative to UGA boundaries
        arcpy.AddMessage("Calculating subject property buffer...")
        uga_layer_name = "Urban Growth Area (UGA)"
        uga_layer_obj = find_layer(list_map_obj, map_name, uga_layer_name)
        subject_prop_lyr = "Subject Property Layer"
        arcpy.MakeFeatureLayer_management(in_features=subject_prop_fc_path, out_layer=subject_prop_lyr)
        arcpy.MakeFeatureLayer_management(in_features=uga_layer_obj, out_layer="uga_lyr")
        arcpy.AddMessage("Selecting subject property location if center is in UGA polygon features...")
        arcpy.SelectLayerByLocation_management(in_layer=subject_prop_lyr,
                                               overlap_type="HAVE_THEIR_CENTER_IN",
                                               select_features="uga_lyr",
                                               selection_type="NEW_SELECTION")
        select_count = int(arcpy.GetCount_management(in_rows=subject_prop_lyr)[0])
        arcpy.SelectLayerByAttribute_management(in_layer_or_view=subject_prop_lyr, selection_type="CLEAR_SELECTION")
        if select_count == 0:
            arcpy.AddMessage("The subject property is outside of any UGAs, generating 1000ft buffer...")
            buffer_dist = 1000
        else:
            arcpy.AddMessage("Subject property is inside of a UGA, generating 500ft buffer...")
            buffer_dist = 500

        # Generate buffer and add to buffer feature class (empty features first if necessary)
        arcpy.AddMessage("Generating subject property buffer polygon feature....")
        buffer_fc_name = "Radius"
        buffer_fc_memory = r"memory\buffer_fc"
        buffer_memory_lyr = "buffer_layer"
        buffer_fc_filepath = check_fc_exists(aprx, buffer_fc_name)
        arcpy.Buffer_analysis(in_features=subject_prop_lyr, out_feature_class=buffer_fc_memory,
                              buffer_distance_or_field=f"{str(buffer_dist)} Feet",
                              line_side="FULL", dissolve_option="ALL")
        arcpy.MakeFeatureLayer_management(in_features=buffer_fc_memory, out_layer=buffer_memory_lyr)
        empty_and_append(buffer_memory_lyr, buffer_fc_filepath)
        arcpy.RecalculateFeatureClassExtent_management(buffer_fc_filepath)

        # Add buffer distance value to attribute field in buffer feature class
        buffer_field = "BUFF_DIST"
        buffer_fc_lyr = "buffer_fc_lyr"
        arcpy.MakeFeatureLayer_management(in_features=buffer_fc_filepath, out_layer=buffer_fc_lyr)
        if not field_exists(buffer_fc_filepath, buffer_field):
            arcpy.AddMessage("Adding a new buffer distance attribute field...")
            arcpy.AddField_management(in_table=buffer_fc_lyr, field_name=buffer_field, field_type="SHORT")
        arcpy.AddMessage("Updating the attribute value in the buffer distance field...")
        arcpy.CalculateField_management(in_table=buffer_fc_lyr, field=buffer_field,
                                        expression=buffer_dist, expression_type="PYTHON3")

        # Get extent of subject property feature
        arcpy.AddMessage("Calculating extent of subject property feature...")
        arcpy.SelectLayerByAttribute_management(in_layer_or_view=subject_prop_lyr, selection_type="NEW_SELECTION")
        subject_prop_lyr_extent = arcpy.da.Describe("Subject Property")['extent']
        subject_prop_lyr_extent_obj = arcpy.Extent(subject_prop_lyr_extent.XMin,
                                                   subject_prop_lyr_extent.YMin,
                                                   subject_prop_lyr_extent.XMax,
                                                   subject_prop_lyr_extent.YMax)
        arcpy.SelectLayerByAttribute_management(in_layer_or_view=subject_prop_lyr, selection_type="CLEAR_SELECTION")

        # Get extent of subject property boundary feature
        arcpy.AddMessage("Calculating extent of subject property buffer...")
        arcpy.SelectLayerByAttribute_management(in_layer_or_view=buffer_fc_lyr, selection_type="NEW_SELECTION")
        buffer_lyr_extent = arcpy.da.Describe(buffer_fc_lyr)["extent"]
        buffer_lyr_extent_obj = arcpy.Extent(buffer_lyr_extent.XMin,
                                             buffer_lyr_extent.YMin,
                                             buffer_lyr_extent.XMax,
                                             buffer_lyr_extent.YMax)
        arcpy.SelectLayerByAttribute_management(in_layer_or_view=buffer_fc_lyr, selection_type="CLEAR_SELECTION")

        # Zoom to extent of subject property feature
        arcpy.AddMessage("Updating extent of layouts...")
        for lyt in list_layout_obj:
            mapframe_list = lyt.listElements("MAPFRAME_ELEMENT")
            for mf in mapframe_list:
                if mf.map.name == "Map_Aerial":
                    mf.camera.setExtent(subject_prop_lyr_extent_obj)
                    mf.camera.scale = mf.camera.scale * 2.5
                elif mf.map.name == "Map_OZMap":
                    mf.camera.setExtent(buffer_lyr_extent_obj)
                    mf.camera.scale = mf.camera.scale * 1.5

        # Update text elements
        arcpy.AddMessage("Updating text elements of layouts...")
        for lyt in list_layout_obj:
            element_list = lyt.listElements("TEXT_ELEMENT")
            for element in element_list:
                if "PFN Large Text" == element.name:
                    element.text = f"PFN {params[1].valueAsText}"
                elif "Project Name Large Text" == element.name:
                    element.text = params[0].valueAsText
                elif "Project Manager Text" == element.name:
                    element.text = f"Project Manager: {params[2].valueAsText}"
                elif "CartCode Text" == element.name:
                    element.text = f"Cart. Code: {params[4].valueAsText}"
                elif "Project Folder Name Text" == element.name:
                    element.text = f"Project Folder Name: {params[0].valueAsText}"
                else:
                    continue

        # aprx.saveACopy(r"C:\Users\SCDJ2L\dev\LUPermitToolbox\PermitMaps_TEST_export.aprx")
        aprx.save()
        aprx.closeViews()

        # Generate safe version of PFN
        pfn_id = params[1].valueAsText
        pfn_safe_name = pfn_id.strip().replace(" ", "_").replace('-', '_')

        # Export layouts to PDF files
        export_filepath = r"C:\Users\SCDJ2L\dev\LUPermitToolbox\graphics"
        for lyt in list_layout_obj:
            if lyt.name == "Layout_AerialVicinity":
                arcpy.AddMessage(f"Exporting {lyt.name} to \graphics folder...")
                lyt.openView()
                lyt.exportToPDF(out_pdf=f"{export_filepath}\\{pfn_safe_name}_Permits_Aerial.pdf", resolution=250,
                                georef_info=False)

            elif lyt.name == "Layout_OZMap":
                arcpy.AddMessage(f"Exporting {lyt.name} to \graphics folder...")
                lyt.openView()
                lyt.exportToPDF(out_pdf=f"{export_filepath}\\{pfn_safe_name}_Permits_OZMap.pdf", resolution=250,
                                georef_info=False)

        arcpy.AddMessage("Land Use Permit reporting process completed successfully!")

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


# Helper functions

# Iterate through relevant maps and layouts and:
def list_map_objects(aprx_obj, prefix="Map_*"):
    """
    Lists map objects in the APRX file that have a specific prefix in their name.

    :param aprx_path: Path to the APRX file.
    :param prefix: The prefix to search for in map names.
    :return: List of map names with the specified prefix.
    """
    map_list = [m for m in aprx_obj.listMaps(prefix)] #if m.name.startswith(prefix)
    return map_list


def list_layout_objects(aprx_obj):
    """
    Lists all layout objects in the APRX file.

    :param aprx_path: Path to the APRX file.
    :return: List of layout objects.
    """
    layout_list = (aprx_obj.listLayouts())
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
        if not layer_obj:
            arcpy.AddWarning(f"No layers matching {layer_name} were found!")
        else:
            arcpy.AddMessage(f"Layer {layer_name} was found in {map_name}...")
            return layer_obj[0]

    except IndexError:
        arcpy.AddError("List of map objects is empty or invalid!")
        return None
    except Exception as e:
        arcpy.AddError(f"{str(e)}")
        return None


def extract_fc_to_memory(src_lyr, query_string, target_lyr=r"memory\selected_features"):
    arcpy.AddMessage(f"Extracting features from {src_lyr} to memory...")
    arcpy.SelectLayerByAttribute_management(in_layer_or_view=src_lyr,
                                            selection_type="NEW_SELECTION",
                                            where_clause=query_string)
    arcpy.CopyFeatures_management(in_features=src_lyr, out_feature_class=target_lyr)
    arcpy.SelectLayerByAttribute_management(in_layer_or_view=src_lyr, selection_type="CLEAR_SELECTION")
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
    arcpy.Append_management(inputs=input_layer, target=input_target_fc, schema_type="NO_TEST")
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


def field_exists(input_fc, field_name):
    """
    Check if a field exists in a feature class.

    :param input_fc: Path to the feature class.
    :param field_name: Name of the attribute field to check for.
    :return: True if the field exists, False if it does not.
    """
    attribute_fields = arcpy.ListFields(input_fc)
    for field in attribute_fields:
        if field.name == field_name:
            return True
    return False
