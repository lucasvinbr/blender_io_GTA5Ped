import bpy
import os.path
import traceback
import bmesh
from mathutils import *
from . import reader_utils
from . import mesh_geometry_utils as geomutils
from . import exporter_utils


def export_selected_mesh(context, filepath):
    print("export to GTA5 .mesh: begin")

    exportedObject = context.active_object

    if exportedObject is None:
        print("export to GTA5 .mesh: no active object, aborting")
        return

    if exportedObject.type != "MESH":
        print("export to GTA5 .mesh: active object is not a mesh, aborting")
        return

    parentSkel = exportedObject.parent
    isRigged = parentSkel is not None and parentSkel.type == "ARMATURE"

    fileBuilder = exporter_utils.OpenFormatsFileComposer()
    fileBuilder.writeLine("Version 165 32")
    fileBuilder.openBracket()

    fileBuilder.writeLine("Locked False")
    fileBuilder.writeLine("Skinned {}".format(isRigged))

    if isRigged:
        fileBuilder.writeLine("BoneCount {}".format(len(parentSkel.data.bones)))
    else:
        fileBuilder.writeLine("BoneCount 0")

    fileBuilder.writeLine("Mask 255") #I haven't seen another value being used here

    print("export to GTA5 .mesh: retrieving mesh data from object...")
    #now we duplicate the target mesh, break it by materials and parse them into GeometryData objects
    geometryDatas = geomutils.meshobj_to_geometries(exportedObject, parentSkel)

    print("export to GTA5 .mesh: parsing retrieved mesh data...")
    parse_geometryDatas(geometryDatas, fileBuilder)

    fileBuilder.closeBracket()
    print("export to GTA5 .mesh: writing to disk...")
    write_to_file(fileBuilder.textContent, filepath)
    print("export to GTA5 .mesh: end")


def parse_iterableData(iterable):
    """utility method for writing vectors and lists"""
    return " ".join(map(str, iterable))

def parse_iterableFloatData(iterable):
    """utility method for writing vectors and lists, limiting the precision of floats"""
    return " ".join(["{:.8f}".format(numvar) for numvar in iterable])


def parse_geometryDatas(geometryDatas, fileBuilder):
    """adds formatted Bounds and Geometry data to the fileBuilder"""
    fileBuilder.writeLine("Bounds")
    fileBuilder.openBracket()

    for geom in geometryDatas:
        fileBuilder.writeLine("Aabb")
        fileBuilder.openBracket()

        fileBuilder.writeLine(" ".join(["Min", parse_iterableFloatData(geom.bounds["min"])]))
        fileBuilder.writeLine(" ".join(["Max", parse_iterableFloatData(geom.bounds["max"])]))

        fileBuilder.closeBracket()

    fileBuilder.closeBracket()

    fileBuilder.writeLine("Geometries")
    fileBuilder.openBracket()

    for geom in geometryDatas:
        fileBuilder.writeLine("Geometry")
        fileBuilder.openBracket()

        fileBuilder.writeLine("ShaderIndex {}".format(geom.shaderIndex))
        fileBuilder.writeLine("Flags -") #not sure what else could go here
        #this declaration seems to define which parameters must be provided for each vertex.
        #declaration SBED48839 appears to be related to the ped_default.sps shader and requires less and more inferrable params
        fileBuilder.writeLine("VertexDeclaration SBED48839") 

        fileBuilder.writeLine("Indices {}".format(len(geom.indices)))
        fileBuilder.openBracket()

        #there is a line break every 15 indices
        writtenIndices = 0
        while writtenIndices < len(geom.indices):
            fileBuilder.writeLine(parse_iterableData(geom.indices[writtenIndices:min(writtenIndices + 15, len(geom.indices))]))
            writtenIndices += 15

        fileBuilder.closeBracket()

        fileBuilder.writeLine("Vertices {}".format(len(geom.vertPositions)))
        fileBuilder.openBracket()

        for i in range(len(geom.vertPositions)):
            fileBuilder.writeLine(" / ".join([parse_iterableFloatData(geom.vertPositions[i]),
                                              parse_iterableFloatData(geom.boneWeights[i]),
                                              parse_iterableData(geom.boneIndexes[i]),
                                              parse_iterableFloatData(geom.vertNormals[i]),
                                              parse_iterableData([255] * 4), #vertex color? not sure about what this entry means
                                              parse_iterableData([0] * 4), #no idea about this one either, but often it's all zeroes
                                              parse_iterableFloatData(geom.uvCoords[i])
                                              ])) 

        fileBuilder.closeBracket()

        fileBuilder.closeBracket()

    fileBuilder.closeBracket()


def write_to_file(content, filepath):
    f = open(filepath, 'w', encoding='utf-8')
    f.write(content)
    f.close()


from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

class ExportGta5Mesh(Operator, ExportHelper):
    """Generates a .mesh file from the active mesh"""
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
        export_selected_mesh(context, self.filepath)
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
