import bpy
import os.path
import traceback
import bmesh
from mathutils import *
from . import reader_utils
from . import mesh_geometry_utils as geomutils
from . import mesh_geometry_datagather_utils as geomreader
from . import writer_utils


def export_selected_mesh(context, filepath, vertDeclarationType, startingShaderIndex=0):
    print("export to GTA5 .mesh: begin")

    exportedObject = context.active_object

    if exportedObject is None:
        print("export to GTA5 .mesh: no active object, aborting")
        return

    if exportedObject.type != "MESH":
        print("export to GTA5 .mesh: active object is not a mesh, aborting")
        return

    #we expect to start the procedure while in object mode
    bpy.ops.object.mode_set( mode = 'OBJECT' )

    parentSkel = exportedObject.parent
    isRigged = parentSkel is not None and parentSkel.type == "ARMATURE"

    fileBuilder = writer_utils.OpenFormatsFileComposer()
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
    geometryDatas = geomreader.meshobj_to_geometries(exportedObject, parentSkel)

    print("export to GTA5 .mesh: parsing retrieved mesh data...")
    parse_geometryDatas(geometryDatas, fileBuilder, vertDeclarationType, startingShaderIndex)

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


def parse_geometryDatas(geometryDatas, fileBuilder, vertexDeclarationType, startingShaderIndex=0):
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

        fileBuilder.writeLine("ShaderIndex {}".format(startingShaderIndex + geom.shaderIndex))
        fileBuilder.writeLine("Flags -") #not sure what else could go here
        #this declaration seems to define which parameters must be provided for each vertex.
        fileBuilder.writeLine("VertexDeclaration {}".format(vertexDeclarationType)) 
        #S12D0183F -with extra UV and qtangents (used by ped.sps shader)
        #SD7D22350 -with qtangents (used by ped_hair_cutout_alpha.sps)
        #SBED48839 -no extra stuff, doesn't seem to support normal mapping etc (used by ped_default.sps)

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

        write_verts_by_vertdeclaration(fileBuilder, geom, vertexDeclarationType)

        fileBuilder.closeBracket()

        fileBuilder.closeBracket()

    fileBuilder.closeBracket()


def write_verts_by_vertdeclaration(fileBuilder, geom, vertDeclaration):
    if vertDeclaration == 'S12D0183F':
        for i in range(len(geom.vertPositions)):
            fileBuilder.writeLine(" / ".join([parse_iterableFloatData(geom.vertPositions[i]),
                                                parse_iterableFloatData(geom.boneWeights[i]),
                                                parse_iterableData(geom.boneIndexes[i]),
                                                parse_iterableFloatData(geom.vertNormals[i]),
                                                parse_iterableData([255] * 4), #vertex color? not sure about what this entry means
                                                parse_iterableData([0] * 4), #no idea about this one either, but often it's all zeroes
                                                parse_iterableFloatData(geom.uvCoords[i]),
                                                parse_iterableFloatData(geom.uvCoords[i]), #second UV map... we don't use it for now
                                                parse_iterableFloatData(geom.qtangents[i]) #this doesn't seem to be the qtangent, actually
                                                ])) 
    elif vertDeclaration == 'SD7D22350':
        for i in range(len(geom.vertPositions)):
            fileBuilder.writeLine(" / ".join([parse_iterableFloatData(geom.vertPositions[i]),
                                                parse_iterableFloatData(geom.boneWeights[i]),
                                                parse_iterableData(geom.boneIndexes[i]),
                                                parse_iterableFloatData(geom.vertNormals[i]),
                                                parse_iterableData([255] * 4), #vertex color? not sure about what this entry means
                                                parse_iterableData([0] * 4), #no idea about this one either, but often it's all zeroes
                                                parse_iterableFloatData(geom.uvCoords[i]),
                                                parse_iterableFloatData(geom.qtangents[i]) #this doesn't seem to be the qtangent, actually
                                                ])) 
    elif vertDeclaration == 'SBED48839':
        for i in range(len(geom.vertPositions)):
            fileBuilder.writeLine(" / ".join([parse_iterableFloatData(geom.vertPositions[i]),
                                                parse_iterableFloatData(geom.boneWeights[i]),
                                                parse_iterableData(geom.boneIndexes[i]),
                                                parse_iterableFloatData(geom.vertNormals[i]),
                                                parse_iterableData([255] * 4), #vertex color? not sure about what this entry means
                                                parse_iterableData([0] * 4), #no idea about this one either, but often it's all zeroes
                                                parse_iterableFloatData(geom.uvCoords[i])
                                                ])) 


def write_to_file(content, filepath):
    f = open(filepath, 'w', encoding='utf-8')
    f.write(content)
    f.close()


from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty
from bpy.types import Operator

class ExportGta5Mesh(Operator):
    """Generates a .mesh file from the active mesh"""
    bl_idname = "io_gta5ped.export_mesh"
    bl_label = "Export GTA5 Ped Mesh (.mesh)"

    filename_ext = ".mesh"

    filepath : StringProperty(
        subtype='FILE_PATH',
    )

    filename : StringProperty(
            name="File Name",
            description="Name used by the exported file",
            maxlen=255,
            subtype='FILE_NAME',
            )

    filter_glob: StringProperty(
        default="*.mesh",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    vertDeclarationType: EnumProperty(
        name="Vertex Declaration Type",
        description="""The declaration affects which entries of the geometry's data will be stored.
         This defines which type of GTA shader the mesh can use.""",
        items=(
            ('S12D0183F', "High Opaque (S12D0183F)", "Used in high LOD meshes; supports the ped.sps shader; stores the most information"),
            ('SD7D22350', "High Alpha (SD7D22350)", "Used in high LOD meshes that have some transparency, like hair; supports the ped_hair_cutout_alpha.sps shader"),
            ('SBED48839', "Low (SBED48839)", "Used in med and low LOD meshes; supports the ped_default.sps shader; stores the least information"),
        ),
        default='S12D0183F',
    )

    startingShaderIndex: IntProperty(
        name="Starting ShaderIndex",
        description="The ShaderIndex of the object's first material will be set to this value. The next one will be this value plus one, and so on",
        default=0,
    )


    def execute(self, context):
        export_selected_mesh(context, self.filepath, self.vertDeclarationType, self.startingShaderIndex)
        return {'FINISHED'}

    def invoke(self, context, event):
        exportedObject = context.active_object
        if exportedObject is not None:
            self.filename = exportedObject.name

        if not self.filepath:
            blend_filepath = context.blend_data.filepath
            if not blend_filepath:
                blend_filepath = "untitled"
            else:
                blend_filepath = os.path.splitext(blend_filepath)[0]
                self.filepath = os.path.join(os.path.dirname(blend_filepath), self.filename + self.filename_ext)
        else:
            self.filepath = os.path.join(os.path.dirname(self.filepath), self.filename + self.filename_ext)


        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportGta5Mesh.bl_idname, text="Export GTA5 Ped Mesh (.mesh)")


def register():
    bpy.utils.register_class(ExportGta5Mesh)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportGta5Mesh)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
