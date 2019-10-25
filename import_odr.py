import bpy
import os.path
import traceback
from mathutils import *
from . import readerutils

def import_odr_from_file(filepath):
    filename = os.path.splitext(os.path.basename(filepath))[0]
    print("Import GTAV ODR {} : begin".format(filename))
    with open(filepath, 'r', encoding='utf-8') as reader:
        string_to_odr(reader, filename, filepath)

    return {'FINISHED'}


def string_to_odr(reader, odrName, odrPath):
    #keep reading until we reach an empty line (end of file)
    line = reader.readline()
    
    odrData = ODRData()
    odrData.path = odrPath

    while line != '':
        check_relevant_section_start(reader, line, odrData)
        line = reader.readline()

    if line == '':
        return

def check_relevant_section_start(reader, line, odrData):
    """checks the line content for names of sections of interest, like Shaders"""
    if "Shaders" in line:
        parse_shaders(reader, line, odrData)
    elif "Skeleton" in line:
        parse_skeleton(reader, line, odrData)
    elif "LodGroup" in line:
        parse_lodgroups(reader, line)


def parse_skeleton(reader, line, odrData):
    #if not null, a relative path to the skel file is declared
    skelPath = line.strip().split(" ")[1]
    if skelPath != "null":
        odrPath = os.path.dirname(odrData.path)
        odrData.skeletonFile = odrPath + skelPath

def parse_shaders(reader, line, odrData):
    while "}" not in line:
        if ".sps" in line:
            odrData.shaders.append(parse_shader_data(reader, line, odrData))
        line = reader.readline()


def parse_shader_data(reader, line, odrData):
    shader = ODRShader()
    #we start in the "shader type" line
    shader.shaderType = line.strip().split(".")[0]
    while "}" not in line:
        if "DiffuseSampler" in line:
            shader.diffuseSampler = line.strip().split(" ")[1]
        elif "BumpSampler" in line:
            samplerName = line.strip().split(" ")[1]
            if samplerName != "*NULL*" and samplerName != "dummy_normal":
                shader.bumpSampler = samplerName
        elif "SpecSampler" in line:
            samplerName = line.strip().split(" ")[1]
            if samplerName != "*NULL*" and samplerName != "dummy_spec":
                shader.specSampler = samplerName
        elif "Bumpiness" in line:
            shader.bumpiness = float(line.strip().split(" ")[1])
        line = reader.readline()

    return shader


class ODRData:
    def __init__(self):
        self.path = None
        self.shaders = []
        self.skeletonFile = None
        self.meshes = []

class ODRShader:
    def __init__(self):
        self.shaderType = None
        self.diffuseSampler = None
        self.bumpSampler = None
        self.specSampler = None
        self.bumpiness = 1.0


from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

class ImportGta5ODR(Operator, ImportHelper):
    """Imports Material, Mesh and Skeleton data"""
    bl_idname = "io_gta5ped.import_odr"
    bl_label = "Import GTA5 Ped .ODR File"

    # ImportHelper mixin class uses this
    filename_ext = ".odr"

    filter_glob: StringProperty(
        default="*.odr",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return import_odr_from_file(self.filepath)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportGta5ODR.bl_idname, text="Import GTA5 Ped .ODR File")


def register():
    bpy.utils.register_class(ImportGta5ODR)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportGta5ODR)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
