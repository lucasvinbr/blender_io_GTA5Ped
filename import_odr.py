import bpy
import os.path
import traceback
from mathutils import *
from . import reader_utils
from . import import_skel
from . import import_mesh



def import_odr_from_file(filepath, alsoApplyData = True):
    filename = os.path.splitext(os.path.basename(filepath))[0]
    print("Import GTAV ODR {} : begin".format(filename))
    with open(filepath, 'r', encoding='utf-8') as reader:
        odrData = string_to_odr(reader, filename, filepath)

    if alsoApplyData:
        apply_odr_data(odrData)

    return {'FINISHED'}


def string_to_odr(reader, odrName, odrPath):
    """returns an ODRData with the info gathered from the file"""
    #keep reading until we reach an empty line (end of file)
    line = reader.readline()
    
    odrData = ODRData()
    odrData.path = odrPath

    while line != '':
        check_relevant_section_start(reader, line, odrData)
        line = reader.readline()

    print("done reading ODR data from file {}".format(odrName))

    return odrData


def apply_odr_data(odrData):
    """runs import procedures for the data contained in the provided ODRData object"""
    print("applying data from ODR: {}".format(odrData.path)) 
    
    importedSkel = None
    importedGeoms = []

    if odrData.skeletonFile is not None:
        importedSkel = import_skel.import_skel_from_file(odrData.skeletonFile)

    for meshPath in odrData.meshPaths:
        importedGeoms.extend(import_mesh.import_mesh_from_file(meshPath))

    if importedSkel is not None:
        #meshes already have weights linked to bone indices;
        #we just have to rename vertex groups to the right names
        for importedMesh in importedGeoms:
            rig_geometry_to_skel(importedMesh, importedSkel)

    

def check_relevant_section_start(reader, line, odrData):
    """checks the line content for names of sections of interest, like Shaders"""
    if "Shaders" in line:
        parse_shaders(reader, line, odrData)
    elif "Skeleton" in line:
        parse_skeleton(reader, line, odrData)
    elif "LodGroup" in line:
        parse_lodgroups(reader, line, odrData)


def parse_lodgroups(reader, line, odrData):
    print("parsing lodmodels...")
    while "}" not in line:
        if "High" in line or "Med" in line or "Low" in line or "Vlow" in line:
            #the parsing func takes care of moving the reader in this case
            line = parse_lodmodel_data(reader, line, odrData)
        else:
            line = reader.readline()


def parse_lodmodel_data(reader, line, odrData):
    #starting from the "model category" (high, med etc) line, check if we open curly braces in the next line
    #if we don't, we probably don't have a model declared for this LOD level
    line = reader.readline()
    if "{" in line:
        line = reader.readline()
        meshPath = line.strip().split(" ")[0]
        if meshPath != "null":
            odrPath = os.path.dirname(odrData.path)
            meshPath = os.path.join(odrPath, meshPath)
            odrData.meshPaths.append(meshPath)
            print("reference to mesh at {}".format(meshPath))
        #get past the "}" line to make the parser keep going
        line = reader.readline()
        line = reader.readline()

    return line
        

def parse_skeleton(reader, line, odrData):
    #if not null, a relative path to the skel file is declared
    skelPath = line.strip().split(" ")[1]
    if skelPath != "null":
        odrPath = os.path.dirname(odrData.path)
        #odrData.skeletonFile = odrPath + skelPath
        odrData.skeletonFile = os.path.join(odrPath, skelPath)
        print("got skeleton at {}".format(odrData.skeletonFile))

def parse_shaders(reader, line, odrData):
    while "}" not in line:
        if ".sps" in line:
            odrData.shaders.append(parse_shader_data(reader, line, odrData))

        line = reader.readline()


def parse_shader_data(reader, line, odrData):
    shader = ODRShader()
    #we start in the "shader type" line
    shader.shaderType = line.strip().split(".")[0]
    print("parsing shader {}".format(shader.shaderType))
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

def rig_geometry_to_skel(geometry, skel):
    """attaches the geometry mesh to the skel (armature modifier and stuff)
    and renames vertex groups according to their indices, so that they match the skel's bones"""
    geometry.meshObj.parent = skel
    armatureMod = geometry.meshObj.modifiers.new("Armature", 'ARMATURE')
    armatureMod.object = skel

    vgroups = geometry.meshObj.vertex_groups

    for i, bone in enumerate(skel.pose.bones):
        if vgroups.find(str(i)) != -1:
            vgroups[str(i)].name = bone.name


class ODRData:
    def __init__(self):
        self.path = None
        self.shaders = []
        self.skeletonFile = None
        self.meshPaths = []

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
