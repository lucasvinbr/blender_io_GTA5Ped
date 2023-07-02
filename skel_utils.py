import bpy
from mathutils import *


def create_new_bone(armature, boneName, parentPoseBone = None):
    """goes into edit mode, creates a new bone with the target parent, then exits edit mode"""
    bpy.ops.object.mode_set(mode="EDIT")
    
    newEditBone = armature.edit_bones.new(boneName)
    
    boneData = GTABone()
    
    #print("creating new bone: {}, parent: {}".format(newEditBone.name, parentPoseBone))
    
    if parentPoseBone is not None:
        parentBone = armature.edit_bones[parentPoseBone.name]
        newEditBone.parent = parentBone
        #newEditBone.use_connect = True
        newEditBone.head = parentPoseBone.head
        #print("set head to parent's pose head: {}".format(parentPoseBone.head))
        newEditBone.tail = parentPoseBone.tail
    else:
        #print("no parent, setting tail: {}".format(newEditBone.head))
        newEditBone.tail = newEditBone.head
        newEditBone.tail.y -= 0.02
        
    newBoneName = newEditBone.name
    
    bpy.ops.object.mode_set(mode="POSE")
    
    boneData.name = newBoneName
    
    return boneData


def create_new_bone_data(armature, boneName, parentBoneName = None):
    """creates a new bone data with the target parent bone name. just stores the data, does not create any bone!"""
    
    boneData = GTABone()
    
    boneData.name = boneName
    boneData.parentBoneName = parentBoneName
    
    return boneData


def recursive_build_bones_from_data(armature, armatureObj, boneDataDict):
    """keeps building bone hierarchies until all bones are built"""

    for boneName, boneData in boneDataDict.items():
        recursive_build_bone_hierarchy(armature, armatureObj, boneData, boneDataDict)



def recursive_build_bone_hierarchy(armature, armatureObj, boneData, boneDataDict):
    """goes into edit mode, creates a new bone with its parent(s), then exits edit mode"""

    bpy.ops.object.mode_set(mode="POSE")
    if armatureObj.pose.bones.get(boneData.name) is None:
        if boneData.parentBoneName is not None and boneData.parentBoneName != '':
            #find parent and, if not yet built, build them before proceeding
            if armatureObj.pose.bones.get(boneData.parentBoneName) is None:
                recursive_build_bone_hierarchy(armature, armatureObj, boneDataDict[boneData.parentBoneName], boneDataDict)
        bpy.ops.object.mode_set(mode="EDIT")
        newEditBone = armature.edit_bones.new(boneData.name)
            
        #print("creating new bone: {}, parent: {}".format(newEditBone.name, parentPoseBone))
        
        if boneData.parentBoneName is not None and boneData.parentBoneName != '':
            parentBone = armature.edit_bones[boneData.parentBoneName]
            newEditBone.parent = parentBone
            #newEditBone.use_connect = True
            #child's head connects to the parent's tail
            #newEditBone.head = parentBone.tail
            newEditBone.tail = parentBone.head
            # newEditBone.tail.y += 0.02
            #print("set head to parent's pose head: {}".format(parentPoseBone.head))
            
        else:
            #print("no parent, setting tail: {}".format(newEditBone.head))
            newEditBone.tail = newEditBone.head
            # newEditBone.tail.y += 0.02
        
        newEditBone.tail += boneData.location
        if newEditBone.head == newEditBone.tail:
            newEditBone.tail.y += 0.02
                
        bpy.ops.object.mode_set(mode="POSE")


def apply_bone_data(boneData):
    #print("applying gathered bone data for bone {}".format(boneData.name))
    
    poseBone = boneData.poseBone
    
    if boneData.rotationQuat is not None:
        #rotMat = boneData.rotationQuat.to_matrix()
#        boneData.rotationQuat = rotMat.inverted().transposed().to_quaternion()
        #boneData.rotationQuat = boneData.rotationQuat.conjugated()
        poseBone.rotation_quaternion.x = boneData.rotationQuat.x
        poseBone.rotation_quaternion.y = boneData.rotationQuat.y
        poseBone.rotation_quaternion.z = boneData.rotationQuat.z
        poseBone.rotation_quaternion.w = boneData.rotationQuat.w
        
        #poseBone.location = poseBone.rotation_quaternion @ poseBone.location
        
        #print("applied rotation {}".format(poseBone.rotation_quaternion))

    if boneData.location is not None:
        poseBone.location.x = boneData.location.x
        poseBone.location.y = boneData.location.y
        poseBone.location.z = boneData.location.z
        
        #print("LOC BEFORE QUAT MULT : {}".format(poseBone.location))
                
        #print("applied location {}".format(poseBone.location))
    if boneData.scale is not None:
        if "SKEL_ROOT" in boneData.name:
            poseBone.scale.x = boneData.scale.x
        else:
            poseBone.scale.x = boneData.scale.x
        poseBone.scale.y = boneData.scale.y
        poseBone.scale.z = boneData.scale.z
        
    
    
    
        
def create_armature(armatureName):
    """Creates an armature object and adds it to the current collection"""
    armature = bpy.data.armatures.new(armatureName)
    armatureObj = bpy.data.objects.new(armatureName, armature)
    
    bpy.context.scene.collection.objects.link(armatureObj)
    
    return armature, armatureObj


def delete_armature(armature):
    """Deletes the target armature (armature obj will also be deleted)"""
    bpy.data.armatures.remove(armature)


class GTABone:
    def __init__(self):
        self.name = None
        self.poseBone = None
        self.location = None
        self.rotationQuat = None
        self.scale = None
        self.parentBoneName = None
