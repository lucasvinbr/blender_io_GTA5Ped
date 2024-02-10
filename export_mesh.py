import bpy
import os.path
import traceback
import bmesh
from mathutils import *
from . import reader_utils
from . import mesh_geometry_utils as geomutils
from . import mesh_geometry_datagather_utils as geomreader
from . import writer_utils


def export_procedure_start(context, filepath, vertDeclarationType, startingShaderIndex=0, exportAllSelected=False):
    if exportAllSelected:
        if len(context.selected_objects) > 0:
            targetDir = os.path.dirname(filepath)
            for obj in context.selected_objects:
                destPath = os.path.join(targetDir, obj.name + ".mesh")
                export_target_object(obj, destPath, vertDeclarationType, startingShaderIndex)
        else:
            print("No objects selected, aborting")
    else:
        export_target_object(context.active_object, filepath, vertDeclarationType, startingShaderIndex)


def export_target_object(targetObj, filepath, vertDeclarationType, startingShaderIndex=0):
    print("export to GTA5 .mesh: begin")

    if targetObj is None:
        print("export to GTA5 .mesh: no active object, aborting")
        return

    print("target mesh: {}".format(targetObj.name))

    if targetObj.type != "MESH":
        print("export to GTA5 .mesh: active object is not a mesh, aborting")
        return

    #we expect to start the procedure while in object mode
    #...but we only want to do it if something's active
    bpy.context.view_layer.objects.active = targetObj
    bpy.ops.object.mode_set( mode = 'OBJECT' )

    parentSkel = targetObj.parent
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
    geometryDatas = geomreader.meshobj_to_geometries(targetObj, parentSkel)

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

def parse_iterableIntData(iterable):
    """utility method for writing vectors and lists, limiting the precision to integers"""
    return " ".join(["{:.0f}".format(numvar) for numvar in iterable])


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

def adjust_bone_weights(weights):
    """
    GTA5 requires bone weights to be normalized and quantized in the 0-255 range. 
    Otherwise it can happen that vertex positions become distorted. Especial for facial bones.
    As weights are stored as floats in blender and the mesh file we have to adjust the float values
    to be in sync with their integer counterpart.
    """
    wSum = sum(weights)
    if wSum <= 0: return weights

    # first normalize weights
    # usually incoming weights are already normalised - but to be on the save side
    Max = max(weights)
    weights_normalised = [weight / wSum for weight in weights]

    # convert to 0-255 range
    weights_normalised_255 = [round(weight_normalised * 255) for weight_normalised in weights_normalised]

    # fix normalisation by making sure the sum is always 255
    wSum_255 = sum(weights_normalised_255)
    wSumOffset = 255 - wSum_255
    if wSumOffset != 0:
        step = 1 if wSumOffset > 0 else -1
        while wSumOffset != 0:
            for idx in range(len(weights_normalised_255)):
                if(weights_normalised_255[idx] > 0):
                    weights_normalised_255[idx] += step
                    wSumOffset -= step
                if wSumOffset == 0: break

    # convert back into 0-1 range
    weights_adjusted = [weight_normalised_255 / 255 for weight_normalised_255 in weights_normalised_255]

    return weights_adjusted

def write_verts_by_vertdeclaration(fileBuilder, geom, vertDeclaration):
    if vertDeclaration == 'S12D0183F':
        for i in range(len(geom.vertPositions)):
            fileBuilder.writeLine(" / ".join([parse_iterableFloatData(geom.vertPositions[i]),
                                                parse_iterableFloatData(adjust_bone_weights(geom.boneWeights[i])),
                                                parse_iterableData(geom.boneIndexes[i]),
                                                parse_iterableFloatData(geom.vertNormals[i]),
                                                parse_iterableIntData(geom.vColor[i]*255),
                                                parse_iterableIntData(geom.vColor2[i]*255),
                                                parse_iterableFloatData(geom.uvCoords[i]),
                                                parse_iterableFloatData(geom.uvCoords2[i]), #second UV map... not always used
                                                parse_iterableFloatData(geom.qtangents[i])
                                                ])) 
    elif vertDeclaration == 'SD7D22350':
        for i in range(len(geom.vertPositions)):
            fileBuilder.writeLine(" / ".join([parse_iterableFloatData(geom.vertPositions[i]),
                                                parse_iterableFloatData(adjust_bone_weights(geom.boneWeights[i])),
                                                parse_iterableData(geom.boneIndexes[i]),
                                                parse_iterableFloatData(geom.vertNormals[i]),
                                                parse_iterableIntData(geom.vColor[i]*255),
                                                parse_iterableIntData(geom.vColor2[i]*255),
                                                parse_iterableFloatData(geom.uvCoords[i]),
                                                parse_iterableFloatData(geom.qtangents[i])
                                                ])) 
    elif vertDeclaration == 'SBED48839':
        for i in range(len(geom.vertPositions)):
            fileBuilder.writeLine(" / ".join([parse_iterableFloatData(geom.vertPositions[i]),
                                                parse_iterableFloatData(adjust_bone_weights(geom.boneWeights[i])),
                                                parse_iterableData(geom.boneIndexes[i]),
                                                parse_iterableFloatData(geom.vertNormals[i]),
                                                parse_iterableIntData(geom.vColor[i]*255),
                                                parse_iterableIntData(geom.vColor2[i]*255),
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

    exportAllSelected: BoolProperty(
        name="Export All Selected Meshes",
        description="""Enable batch export of all selected meshes instead of only the active one. 
    WARNING: the meshes' names will be used instead of the provided filename! Only the directory will be considered""",
        default=False,
    )


    def execute(self, context):
        export_procedure_start(context, self.filepath, self.vertDeclarationType, self.startingShaderIndex, self.exportAllSelected)
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
