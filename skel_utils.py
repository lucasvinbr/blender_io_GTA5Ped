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


def apply_bone_data(boneData):
    #print("applying gathered bone data for bone {}".format(boneData.name))
    
    poseBone = boneData.poseBone
    
    if boneData.rotationQuat is not None:
        #rotMat = boneData.rotationQuat.to_matrix()
#        boneData.rotationQuat = rotMat.inverted().transposed().to_quaternion()
        #boneData.rotationQuat = boneData.rotationQuat.conjugated()
        poseBone.rotation_quaternion.w = -boneData.rotationQuat.z
        poseBone.rotation_quaternion.x = boneData.rotationQuat.y
        poseBone.rotation_quaternion.y = -boneData.rotationQuat.x
        poseBone.rotation_quaternion.z = -boneData.rotationQuat.w
        
        #poseBone.location = poseBone.rotation_quaternion @ poseBone.location
        
        #print("applied rotation {}".format(poseBone.rotation_quaternion))

    if boneData.location is not None:
        poseBone.location.x = -boneData.location.x
        poseBone.location.y = -boneData.location.y
        poseBone.location.z = -boneData.location.z
        
        #print("LOC BEFORE QUAT MULT : {}".format(poseBone.location))
                
        #print("applied location {}".format(poseBone.location))
    if boneData.scale is not None:
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