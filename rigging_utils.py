import bpy
from mathutils import *


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