import bpy
import os.path
import traceback
from mathutils import *
from . import reader_utils
from . import skel_utils as skelutils
from math import radians

def import_skel_from_file(filepath):
    """returns an armature object if successful"""
    skelname = os.path.splitext(os.path.basename(filepath))[0]
    print("Import GTAV Skeleton {} : begin".format(skelname))
    with open(filepath, 'r', encoding='utf-8') as reader:
        return string_to_skel(reader, skelname)


def string_to_skel(reader, skelName):
    #the skel file must have a "Version" header
    line = reader_utils.read_until_line_containing(reader,"Version")
    
    if line == '':
        return
    
    print("Version OK")
    
    #store the number of bones declared in the file
    #so that we may know if we succeeded in importing all of them
    line = reader_utils.read_until_line_containing(reader,"NumBones")
    
    if line == '':
        return
    
    boneCount = line.split(" ")[1]
    
    print("Bone count declared in file: {}".format(boneCount))
    
    #jump to the first bone
    line = reader_utils.read_until_line_containing(reader,"Bone ")
    
    if line == '':
        return
    
    print("Reading Armature...")
    armature, armatureObj = skelutils.create_armature(skelName)
    
    armature.display_type = "STICK"
    
    #select new armatureObj, then add bones
    bpy.context.view_layer.objects.active = armatureObj
    
    boneDataList = []
    
    try:
        recursive_parse_bone(reader, line, armature, armatureObj, boneDataList)        
    except Exception as e:
        print("Bone parsing failed! {}.{}".format(e, traceback.format_exc()))
        
        skelutils.delete_armature(armature)
        return
        
    print("Building Armature...")
    for boneData in boneDataList:
        skelutils.apply_bone_data(boneData)
        
    bpy.ops.pose.armature_apply()
    bpy.ops.object.mode_set(mode="OBJECT")
    print("Created skeleton {} successfully".format(skelName))

    # we have to rotate the armature object to face the correct direction
    armatureObj.rotation_euler = (0,0,radians(180))
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = armatureObj
    armatureObj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    return armatureObj
    

def recursive_parse_bone(reader, curReaderLine, armature, armatureObj, boneDataList, parentPoseBone = None):
    """jumps to the next Bone line (if necessary) and creates a new bone and its children"""
    
    if "Bone " not in curReaderLine:
        curReaderLine = reader_utils.read_until_line_containing(reader, "Bone ")
        
        if curReaderLine == '':
            return
        
    #get bone name from cur line and adds it to the armature
    boneName = curReaderLine.split(" ")[1]
    
    boneData = skelutils.create_new_bone(armature, boneName, parentPoseBone)
    
    newPoseBone = armatureObj.pose.bones[boneData.name]
    
    boneData.poseBone = newPoseBone
    
    boneDataList.append(boneData)
    
    while "Children" not in curReaderLine and "}" not in curReaderLine:
        curReaderLine, boneData = parse_bone_dataline(reader, boneData)
                
    if "Children" in curReaderLine:
        childCount = int(curReaderLine.split(" ")[1])
        
        for _ in range(childCount):
            recursive_parse_bone(reader, curReaderLine, armature, armatureObj, boneDataList, newPoseBone)
        

def parse_bone_dataline(reader, boneData):
    """goes to the next line and attempts to retrieve data from it"""
    line = reader.readline()
    
    if "RotationQuaternion" in line:
        lineData = line.split(" ")
        
        boneData.rotationQuat = Quaternion(map(float,lineData[1:]))
        
    elif "LocalOffset" in line:
        lineData = line.split(" ")
        
        boneData.location = Vector(map(float,lineData[1:]))
    
    elif "Scale" in line:
        lineData = line.split(" ")
        
        boneData.scale = Vector(map(float,lineData[1:]))

    return line, boneData


from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

class ImportGta5Skel(Operator, ImportHelper):
    """Imports an armature from a .skel file"""
    bl_idname = "io_gta5ped.import_skel"
    bl_label = "Import GTA5 Ped Skeleton (.skel)"

    # ImportHelper mixin class uses this
    filename_ext = ".skel"

    filter_glob: StringProperty(
        default="*.skel",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        import_skel_from_file(self.filepath)
        return {'FINISHED'}


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportGta5Skel.bl_idname, text="Import GTA5 Ped Skeleton (.skel)")


def register():
    bpy.utils.register_class(ImportGta5Skel)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportGta5Skel)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
