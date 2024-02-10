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
        # Blenders order is [x, y, z, w] but bone Data stores it [w, x, y, z] so we have to shift the values
        poseBone.rotation_quaternion.w = boneData.rotationQuat.z
        poseBone.rotation_quaternion.x = boneData.rotationQuat.w
        poseBone.rotation_quaternion.y = boneData.rotationQuat.x
        poseBone.rotation_quaternion.z = boneData.rotationQuat.y

    if boneData.location is not None:
        # To make it clear: these are local offsets from the parent bone in local space coordinates
        poseBone.location.x = boneData.location.x # x is the bone's forward axis and most offsets are applied here
        poseBone.location.y = boneData.location.y
        poseBone.location.z = boneData.location.z


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