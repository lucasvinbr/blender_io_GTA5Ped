import bpy
import os.path
import traceback
from mathutils import *
from . import reader_utils
from . import import_odr
from . import import_skel


def import_odd_from_file(filepath, alsoApplyData = True):
    filename = os.path.splitext(os.path.basename(filepath))[0]
    print("Import GTAV ODD {} : begin".format(filename))
    with open(filepath, 'r', encoding='utf-8') as reader:
        oddData = string_to_odd(reader, filename, filepath)

    if alsoApplyData:
        print("Applying data from read ODD file {}".format(filename))
        oddData.apply_data()

    return oddData


def string_to_odd(reader, oddName, oddPath):
    """returns an ODDData with the info gathered from the file"""
    #keep reading until we reach an empty line (end of file)
    line = reader.readline()
    
    oddData = ODDData()
    oddData.path = oddPath

    oddDir = os.path.dirname(oddData.path)

    while line != '':
        oddData = parse_line(reader, line, oddData, oddDir)
        line = reader.readline()

    print("done reading ODD data from file {}".format(oddName))

    return oddData


def parse_line(reader, line, oddData, oddDir):
    """just checks the line for an ODR extension and then attempts an import from it if the extension is found"""
    if "odr" in line.lower():
        lineData = line.strip()
        odrPath = os.path.join(oddDir, lineData)
        odrData = import_odr.import_odr_from_file(odrPath, False)
        if odrData is not None:
            oddData.odrDatas.append(odrData)
        else:
            print("Failed import from odr in path {}".format(lineData))
    
    return oddData


class ODDData:
    def __init__(self):
        self.path = None
        self.odrDatas = []

    def apply_data(self):
        """imports all ODRs read from the ODD file. The first skeleton found is set as the override skeleton,
        with whom any ODRs without a skel will be rigged"""

        overrideSkel = None
        overrideSkelPath = None

        for odrData in self.odrDatas:
            if odrData.skeletonFilePath is not None:
                overrideSkel = import_skel.import_skel_from_file(odrData.skeletonFilePath)
                overrideSkelPath = odrData.skeletonFilePath
                break
        
        for odrData in self.odrDatas:
            odrData.apply_data(overrideSkel, overrideSkelPath)



from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

class ImportGta5ODD(Operator, ImportHelper):
    """Imports Material, Mesh and Skeleton data"""
    bl_idname = "io_gta5ped.import_odd"
    bl_label = "Import GTA5 Ped .ODD File"

    # ImportHelper mixin class uses this
    filename_ext = ".odd"

    filter_glob: StringProperty(
        default="*.odd",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        import_odd_from_file(self.filepath)
        return {'FINISHED'}


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportGta5ODD.bl_idname, text="Import GTA5 Ped .ODD File")


def register():
    bpy.utils.register_class(ImportGta5ODD)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportGta5ODD)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
