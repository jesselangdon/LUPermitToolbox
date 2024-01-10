"""
File name:      LUPermitMapToolbox.pyt
Description:    This Python toolbox includes tools for the automated generation of PDF maps associated with PDS Land Use
                project information, which is tracked in AMANDA. This toolbox is based on the

Author:         Jesse Langdon, Principal GIS Analyst
Department:     Snohomish County Planning and Development Services (PDS)
Last Update:    1/10/2024
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
            displayName="PFN",
            name="pfn",
            datatype="DEString",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Carto Code",
            name="carto_code",
            datatype="DEString",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Project Name",
            name="project_name",
            datatype="DEString",
            parameterType="Required",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="Project Manager",
            name="project_manager",
            datatype="DEString",
            parameterType="Required",
            direction="Input")

        param4 = arcpy.Parameter(
            displayName="Tax Account #(s)",
            name="tax_account_number",
            datatype="DEString",
            parameterType="Required",
            direction="Input")

        param5 = arcpy.Parameter(
            displayName="Project Name",
            name="project_name",
            datatype="DEString",
            parameterType="Required",
            direction="Input")

        # param6 - arcpy.Parameter(
        #     displayName="Project Year",
        #     name="project_year",
        #     datatype="DEString",
        #     parameterType="Required",
        #     direction="Input")
        # param6.filter.type = "ValueList"
        # param6.filter.list = [2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014, 2013, 2012]

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
def list_map_objects(aprx_path, prefix="Maps_"):
    """
    Lists map objects in the APRX file that have a specific prefix in their name.

    :param aprx_path: Path to the APRX file.
    :param prefix: The prefix to search for in map names.
    :return: List of map names with the specified prefix.
    """
    aprx = arcpy.mp.ArcGISProject(aprx_path)
    map_list = [m for m in aprx.listMaps() if m.name.startswith(prefix)]
    return map_list


def list_layout_objects(aprx_path):
    """
    Lists all layout objects in the APRX file.

    :param aprx_path: Path to the APRX file.
    :return: List of layout objects.
    """
    aprx = arcpy.mp.ArcGISProjects(aprx_path)
    layout_list = aprx.listLayouts()
    return layout_list


# Build list of sanitized tax account IDs

# Create a safe version of the PFN
# create_safe_pfn (pfn_id):
#   return

# Build definition query for the Subject Property layer based on found tax ID list

# Extract the parcel polygon feature(s) based on the user submitted PFN(s) into memory

# If there is more than one parcel submitted by user, dissolve the parcels into a single polygon feature

# Update the text elements in layout with the APRX and looping through them

# Export the pdf file to supplied directory
# export_pdf(export_pdf_path):
#   return