"""
File name:      LUPermitMapToolbox.pyt
Description:    This Python toolbox includes tools for the automated generation of PDF maps associated with PDS Land Use
                project information, which is tracked in AMANDA. This toolbox is based on the
Author:         Jesse Langdon, Principal GIS Analyst
Department:     Snohomish County Planning and Development Services (PDS)
Last Update:    1/22/2024
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
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="PFN",
            name="pfn_id",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Project Manager",
            name="project_manager",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="Property ID",
            name="property_id",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        param4 = arcpy.Parameter(
            displayName="Carto Code",
            name="carto_code",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

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
        map = "Map_OZMap"
        parcel_layer_name = "Cadastral Parcel"
        found_layer_obj = find_layer(list_map_obj, map, parcel_layer_name)
        if found_layer_obj:
            arcpy.AddMessage(f"Parcel layer found: {found_layer_obj}")
        else:
            arcpy.AddError(f"Parcel layer not found!")

        # Select the subject property features from the cadastral parcel layer, and dissolve (if number of parcels is > 1)
        memory_lyr = dissolve_parcels_to_memory(found_layer_obj, list_parcel_ids, qry_parcel_ids)

        # Empty the subject property feature class in the project file GDB, and append the selected subject property feature
        subject_prop_fc_path = update_subject_prop_fc(aprx, memory_lyr)

        subject_prop_lyr = "Subject Property Layer"
        arcpy.MakeFeatureLayer_management(in_features=subject_prop_fc_path, out_layer=subject_prop_lyr)

        # Calculate buffer distance based on where the subject property is located relative to UGA boundaries
        buffer_dist = get_buffer_distance(list_map_obj, map, subject_prop_lyr)

        # Generate buffer and add to buffer feature class (empty features first if necessary)
        buffer_fc_path = generate_buffer_layer(aprx, subject_prop_lyr, buffer_dist)

        # Add buffer distance value to attribute field in buffer feature class
        buffer_lyr = update_buffer_distance_field(buffer_dist, buffer_fc_path)

        # Get extent of subject property feature and buffer feature
        subject_prop_lyr_extent_obj = get_fc_extent(subject_prop_lyr)
        buffer_lyr_extent_obj = get_fc_extent(buffer_lyr)

        # Zoom to extent of subject property and buffer features
        zoom_to_subject_property(list_layout_obj, subject_prop_lyr_extent_obj, buffer_lyr_extent_obj)

        # Update text elements
        update_text_elements(list_layout_obj, params)

        # Save changes and close any open layout or map views
        aprx.save()
        aprx.closeViews()

        # Generate safe version of PFN
        pfn_safe_name = generate_safe_pfn(params)

        # Export layouts to PDF files
        export_layouts_to_pdf(list_layout_obj, pfn_safe_name)

        arcpy.AddMessage("Land Use Permit maps updated and exported successfully!")

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

    :param aprx_obj: Path to the APRX file.
    :param prefix: The prefix to search for in map names.
    :return: List of map names with the specified prefix.
    """
    map_list = [m for m in aprx_obj.listMaps(prefix)] #if m.name.startswith(prefix)
    return map_list


def list_layout_objects(aprx_obj):
    """
    Lists all layout objects in the APRX file.

    :param aprx_obj: Path to the APRX file.
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

    :param input_parcel_ids: parcel ID in string format
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

    :param input_map_obj_list: list of map objects
    :param layer_name: wildcard string for the layer name
    :return: The layer object if found, otherwise None
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
    """
    Select features from a layer using a supplied query string and copies that to a layer in memoriy

    :param src_lyr: Source layer where the features will be extracted from
    :param query_string: Text string used as a query in the Select process
    :param target_lyr: in memory layer with selected features
    :return: target_lyr
    """
    arcpy.AddMessage(f"Extracting features from {src_lyr} to memory...")
    arcpy.SelectLayerByAttribute_management(in_layer_or_view=src_lyr,
                                            selection_type="NEW_SELECTION",
                                            where_clause=query_string)
    arcpy.CopyFeatures_management(in_features=src_lyr, out_feature_class=target_lyr)
    arcpy.SelectLayerByAttribute_management(in_layer_or_view=src_lyr, selection_type="CLEAR_SELECTION")

    return target_lyr


def check_fc_exists(input_aprx, target_fc):
    """
    Checks if a feature class exists at the filepath supplied by the user

    :param input_aprx: APRX object from which the defalut geodatabase parameter is pulled
    :param target_fc: filepath of the feature class to be checked
    :return:
    """
    default_gdb = input_aprx.defaultGeodatabase
    target_fc_path = os.path.join(default_gdb, target_fc)
    if arcpy.Exists(target_fc_path):
        arcpy.AddMessage(f"{target_fc} found in default geodatabase...")
        return target_fc_path
    else:
        arcpy.AddError(f"Feature class {target_fc} not found in default geodatabase!")

    return


def delete_all_features_in_fc(target_fc_path):
    """
    Deletes all features within a feature class

    :param target_fc_path: Filepath to the feature class
    :return:
    """
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

    :param input_layer: Layer with features that will be used to replace features in the target feature class
    :param input_target_fc: Feature class with features that will be replaced by features in the input layer.
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

    :param list_maps: list of map objects found in the project's APRX object
    :param target_layer_name: Name of the layer object to be found in a map object
    :param data_source_string: String representing the data source (feature class in the default geodatabase)
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


def dissolve_parcels_to_memory(found_layer_object, parcel_id_list, query_parcel):
    """
    Queries the cadastral parcel layer using the input parcel ID values, extracts those parcel to a memory layer,
    then dissolves if there is more than one parcel feature.

    :param found_layer_object: The cadastral parcel layer object found in the Map_OZMap map object
    :param parcel_id_list: list of parcel IDs supplied by user from Python toolbox interface
    :param query_parcel: string with text for querying the parcels, using the parcel IDs
    :return: memory_lyr
    """
    memory_layer_extract = extract_fc_to_memory(found_layer_object, query_parcel)
    memory_layer = r"memory\memory_lyr"
    if len(parcel_id_list) > 1:
        arcpy.AddMessage("There are > 1 parcels. The parcel boundaries will be dissolved...")
        arcpy.Dissolve_management(in_features=memory_layer_extract, out_feature_class=memory_layer)
    else:
        arcpy.MakeFeatureLayer_management(in_features=memory_layer_extract, out_layer=memory_layer)
    return memory_layer


def update_subject_prop_fc(aprx_object, memory_layer):
    """
    Empties the subject property feature class in the project file GDB, and append the selected subject property feature

    :param aprx_object: The project's APRX object
    :param memory_layer: A layer stored in memory with features to be appended to the subject property feature class
    :return: subject_prop_fc_path: Filepath to the subject property feature class
    """
    #
    arcpy.AddMessage("Emptying the subject property feature class of all features...")
    subject_property_fc = "SubjectProperty"
    subject_property_fc_path = check_fc_exists(aprx_object, subject_property_fc)
    empty_and_append(memory_layer, subject_property_fc_path)
    arcpy.RecalculateFeatureClassExtent_management(subject_property_fc_path)
    arcpy.Delete_management(memory_layer)
    return subject_property_fc_path


def get_buffer_distance(map_object_list, map_name, subject_property_layer):
    """
    Calculate buffer size based on where the subject property is located relative to UGA boundaries

    :param map_object_list: list of map objects found in layouts in the project's APRX object
    :param map_name: string representing the target map objects name
    :param subject_property_layer: layer representing subject property feature(s)
    :return: buffer_dist
    """

    arcpy.AddMessage("Calculating subject property buffer...")
    uga_layer_name = "Urban Growth Area (UGA)"
    uga_layer_obj = find_layer(map_object_list, map_name, uga_layer_name)
    arcpy.MakeFeatureLayer_management(in_features=uga_layer_obj, out_layer="uga_lyr")
    arcpy.AddMessage("Selecting subject property location if center is in UGA polygon features...")
    arcpy.SelectLayerByLocation_management(in_layer=subject_property_layer,
                                           overlap_type="HAVE_THEIR_CENTER_IN",
                                           select_features="uga_lyr",
                                           selection_type="NEW_SELECTION")
    select_count = int(arcpy.GetCount_management(in_rows=subject_property_layer)[0])
    arcpy.SelectLayerByAttribute_management(in_layer_or_view=subject_property_layer, selection_type="CLEAR_SELECTION")
    if select_count == 0:
        arcpy.AddMessage("The subject property is outside of any UGAs, generating 1000ft buffer...")
        buffer_dist = 1000
    else:
        arcpy.AddMessage("Subject property is inside of a UGA, generating 500ft buffer...")
        buffer_dist = 500

    return buffer_dist


def generate_buffer_layer(aprx_object, subject_property_layer, buffer_distance):
    """
    Generate buffer feature and add to buffer feature class (empty features first if necessary)

    :param aprx_object: ArcGIS Pro APRX object
    :param subject_property_layer: layer with subject property feature class as the data source
    :param buffer_distance: integer representing the required buffer distance
    :return buffer_fc_filepath: filepath to the buffer feature class
    """
    arcpy.AddMessage("Generating subject property buffer polygon feature....")
    buffer_fc_name = "Radius"
    buffer_fc_memory = r"memory\buffer_fc"
    buffer_memory_lyr = "buffer_memory_layer"
    buffer_fc_filepath = check_fc_exists(aprx_object, buffer_fc_name)
    arcpy.Buffer_analysis(in_features=subject_property_layer, out_feature_class=buffer_fc_memory,
                          buffer_distance_or_field=f"{str(buffer_distance)} Feet",
                          line_side="FULL", dissolve_option="ALL")
    arcpy.MakeFeatureLayer_management(in_features=buffer_fc_memory, out_layer=buffer_memory_lyr)
    empty_and_append(buffer_memory_lyr, buffer_fc_filepath)
    arcpy.RecalculateFeatureClassExtent_management(buffer_fc_filepath)

    return buffer_fc_filepath


def update_buffer_distance_field(buffer_dist, buffer_fc_filepath):
    """
    Add buffer distance value to attribute field in buffer feature class

    :param buffer_dist: integer representing the calculated buffer distance
    :param buffer_fc_filepath: file path to the buffer feature class in the default geodatabase
    :return buffer_layer: layer with the buffer feature class as a data source
    """
    buffer_layer = "buffer_lyr"
    arcpy.MakeFeatureLayer_management(in_features=buffer_fc_filepath, out_layer=buffer_layer)
    buffer_field = "BUFF_DIST"
    if not field_exists(buffer_fc_filepath, buffer_field):
        arcpy.AddMessage("Adding a new buffer distance attribute field...")
        arcpy.AddField_management(in_table=buffer_layer, field_name=buffer_field, field_type="SHORT")
    arcpy.AddMessage("Updating the attribute value in the buffer distance field...")
    arcpy.CalculateField_management(in_table=buffer_layer, field=buffer_field,
                                    expression=buffer_dist, expression_type="PYTHON3")

    return buffer_layer


def get_fc_extent(input_layer):
    """
    Get extent of subject property feature and return as an Extent object

    :param input_layer: target layer
    :param layer_name_string: the name of the target layer as a string
    :return layer_extent_object: Extent object
    """
    arcpy.AddMessage("Calculating extent of subject property feature...")
    arcpy.SelectLayerByAttribute_management(in_layer_or_view=input_layer, selection_type="NEW_SELECTION")
    layer_extent = arcpy.da.Describe(input_layer)['extent']
    layer_extent_object = arcpy.Extent(layer_extent.XMin, layer_extent.YMin, layer_extent.XMax, layer_extent.YMax)
    arcpy.SelectLayerByAttribute_management(in_layer_or_view=input_layer, selection_type="CLEAR_SELECTION")

    return layer_extent_object


def zoom_to_subject_property(layout_object_list, subject_prop_lyr_extent, buffer_lyr_extent):
    """
    Zoom to extent of subject property feature and buffer feature

    :param layout_object_list: list of layout objects found in the project's APRX object
    :param subject_prop_lyr_extent: extent object for the feature in the subject property layer
    :param buffer_lyr_extent: extent object for the buffer layer
    :return:
    """
    arcpy.AddMessage("Zoom layouts to extent of subject property and buffer...")
    for lyt in layout_object_list:
        mapframe_list = lyt.listElements("MAPFRAME_ELEMENT")
        for mf in mapframe_list:
            if mf.map.name == "Map_Aerial":
                mf.camera.setExtent(subject_prop_lyr_extent)
                mf.camera.scale = mf.camera.scale * 2.5
            elif mf.map.name == "Map_OZMap":
                mf.camera.setExtent(buffer_lyr_extent)
                mf.camera.scale = mf.camera.scale * 1.5
    return


def update_text_elements(layout_object_list, input_params):
    """
    Updates project name, project folder number (PFN), project manager, and cartographic code text elements in layouts

    :param layout_object_list: list of layout objects pulled from the APRX object
    :param input_params: list of parameter objects from the getParameterInfo method of the GenerateLUMapTool class
    :return:
    """
    arcpy.AddMessage("Updating text elements of layouts...")
    for lyt in layout_object_list:
        element_list = lyt.listElements("TEXT_ELEMENT")
        for element in element_list:
            if "PFN Large Text" == element.name:
                element.text = f"PFN {input_params[1].valueAsText}"
            elif "Project Name Large Text" == element.name:
                element.text = input_params[0].valueAsText
            elif "Project Manager Text" == element.name:
                element.text = f"Project Manager: {input_params[2].valueAsText}"
            elif "CartCode Text" == element.name:
                element.text = f"Cart. Code: {input_params[4].valueAsText}"
            elif "Project Folder Name Text" == element.name:
                element.text = f"Project Folder Name: {input_params[0].valueAsText}"
            else:
                continue

    return


def generate_safe_pfn(input_params):
    """
    Generates a safe version of PFN as a string

    :param input_params: list of parameter objects from the getParameterInfo method of the GenerateLUMapTool class
    :return pfn_safe_name: PFN string with all spaces and "-" characters replaced with underscores
    """
    pfn_id = input_params[1].valueAsText
    pfn_safe_name = pfn_id.strip().replace(" ", "_").replace('-', '_')

    return pfn_safe_name


def export_layouts_to_pdf(layout_object_list, input_pfn):
    """
    Export both layouts to PDF files

    :param layout_object_list: List of layout objects found in the project's APRX object
    :param input_pfn: sanitized PFN value as string
    :return:
    """
    export_filepath = r"C:\Users\SCDJ2L\dev\LUPermitToolbox\graphics"
    for lyt in layout_object_list:
        if lyt.name == "Layout_AerialVicinity":
            arcpy.AddMessage(f"Exporting {lyt.name} to \graphics folder...")
            lyt.openView()
            lyt.exportToPDF(out_pdf=f"{export_filepath}\\{input_pfn}_Permits_Aerial.pdf", resolution=250,
                            georef_info=False)

        elif lyt.name == "Layout_OZMap":
            arcpy.AddMessage(f"Exporting {lyt.name} to \graphics folder...")
            lyt.openView()
            lyt.exportToPDF(out_pdf=f"{export_filepath}\\{input_pfn}_Permits_OZMap.pdf", resolution=250,
                            georef_info=False)

    return