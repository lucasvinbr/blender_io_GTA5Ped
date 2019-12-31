import bpy
import os.path
import traceback
import bmesh
from mathutils import *
from . import reader_utils
from . import mesh_geometry_utils as geomutils


from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

class ExportGta5Mesh(Operator, ExportHelper):
    """Generates a .mesh file from a single blender mesh object"""
    bl_idname = "io_gta5ped.export_mesh"
    bl_label = "Export GTA5 Ped Mesh (.mesh)"

    # ExportHelper mixin class uses this
    filename_ext = ".mesh"

    filter_glob: StringProperty(
        default="*.mesh",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        # import_mesh_from_file(self.filepath)
        return {'FINISHED'}


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportGta5Mesh.bl_idname, text="Export GTA5 Ped Mesh (.mesh)")


def register():
    bpy.utils.register_class(ExportGta5Mesh)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportGta5Mesh)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
