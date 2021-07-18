import bpy
import os.path
import traceback
import bmesh
from mathutils import *
from . import reader_utils
from . import mesh_geometry_utils as geomutils


def import_mesh_from_file(filepath):
    """returns a list of ImportedMesh if successful"""
    meshname = os.path.splitext(os.path.basename(filepath))[0]
    print("Import GTAV Mesh {} : begin".format(meshname))
    with open(filepath, 'r', encoding='utf-8') as reader:
        return string_to_mesh(reader, meshname)

def string_to_mesh(reader, meshName):
    #"Version" header
    line = reader_utils.read_until_line_containing(reader,"Version")
    
    if line == '':
        return
    
    print("Version OK")
    
    line = reader_utils.read_until_line_containing(reader,"Geometries")
    
    if line == '':
        return
    
    #jump to the line opening brackets, then to the next one, where we presume the first vert is
    line = reader_utils.read_until_line_containing(reader,"{")
    
    if line == '':
        return
    
    print("Reading Geometries Data...")
    
    try:
        geometries = read_geometries(reader, line)        
    except Exception as e:
        print("Geometry parsing failed! {}.{}".format(e, traceback.format_exc()))
        
    else:
        for geometry in geometries:
            geomutils.build_geometry(geometry, meshName)
        
        print("Joining geometries sharing shaderIndex...")
        geometries = geomutils.join_geometries_sharing_mats(geometries)
        importedMeshes = []
        
        for geom in geometries:
            importedMeshes.append(ImportedMesh(geom.mesh, geom.meshObj, geom.shaderIndex))
        print("mesh import successful")
        return importedMeshes
        

def read_geometries(reader, curReaderLine):
    """calls read_geometry_data for each Geometry entry"""
    #starting from a "{" line... the next one should be a "Geometry"
    curReaderLine = reader.readline()
    
    geometries = []
    
    while "}" not in curReaderLine and curReaderLine != '':
        if "Geometry" in curReaderLine:
            curReaderLine = reader.readline()
            print("Reading Geometry...")
            geometries.append(read_geometry_data(reader, curReaderLine))
        curReaderLine = reader.readline()
              
    return geometries
    

def read_geometry_data(reader, curReaderLine):
    """returns a GeometryData object with the data retrieved"""
    #we expect to start from the "{" line
    curReaderLine = reader.readline()
    
    geomData = geomutils.GeometryData()
    
    while "}" not in curReaderLine and curReaderLine != '':
        if "ShaderIndex" in curReaderLine:
            geomData.shaderIndex = int(curReaderLine.split(" ")[1])
        elif "Indices" in curReaderLine:
            curReaderLine = reader.readline()
            curReaderLine = reader.readline()
            print("Reading Geometry Indices...")
            while "}" not in curReaderLine:
                parse_indices_dataline(curReaderLine, geomData)
                curReaderLine = reader.readline()
        elif "Vertices" in curReaderLine:
            curReaderLine = reader.readline()
            curReaderLine = reader.readline()
            print("Reading Geometry Vertices...")
            while "}" not in curReaderLine:
                parse_vert_dataline(curReaderLine, geomData)
                curReaderLine = reader.readline()
        curReaderLine = reader.readline()
                
    return geomData

    
def parse_indices_dataline(line, geomData):
    """attempts to retrieve indices from the target line"""
    indices = map(int, line.split(" "))
    
    geomData.indices.extend(indices)
    
    return line
    

def parse_vert_dataline(line, geomData):
    """attempts to retrieve vertex data from the target line"""
    
    #data entries are expected to be separated by a " / "
    lineData = line.split("/")
    
    #first entry = position
    lineDataEntry = lineData[0].strip().split(" ")
    #print("vertpos: {}".format(lineDataEntry))
    geomData.vertPositions.append(Vector(map(float,lineDataEntry)))
    
    #weights
    lineDataEntry = lineData[1].strip().split(" ")
    geomData.boneWeights.append(list(map(float, lineDataEntry)))

    #and the bone indexes of the weights
    lineDataEntry = lineData[2].strip().split(" ")
    geomData.boneIndexes.append(lineDataEntry)

    #normals
    lineDataEntry = lineData[3].strip().split(" ")
    geomData.vertNormals.append(Vector(map(float,lineDataEntry)))
    
    #uvs (they are flipped in the y axis!)
    lineDataEntry = Vector(map(float, lineData[6].strip().split(" ")))
    lineDataEntry.y *= -1
    geomData.uvCoords.append(lineDataEntry)

    #second uvs (only available in high opaque)
    if len(lineData) >= 9:
        lineDataEntry = Vector(map(float, lineData[7].strip().split(" ")))
        lineDataEntry.y *= -1
        geomData.uvCoords2.append(lineDataEntry)
    
    return line
    

class ImportedMesh():
    def __init__(self, mesh = None, meshObj = None, shaderIndex = 0):
        self.mesh = mesh
        self.meshObj = meshObj
        self.shaderIndex = shaderIndex


from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

class ImportGta5Mesh(Operator, ImportHelper):
    """Imports a mesh object with UVs and weights (but no skeleton) as declared in the .mesh file"""
    bl_idname = "io_gta5ped.import_mesh"
    bl_label = "Import GTA5 Ped Mesh (.mesh)"

    # ImportHelper mixin class uses this
    filename_ext = ".mesh"

    filter_glob: StringProperty(
        default="*.mesh",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        import_mesh_from_file(self.filepath)
        return {'FINISHED'}


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportGta5Mesh.bl_idname, text="Import GTA5 Ped Mesh (.mesh)")


def register():
    bpy.utils.register_class(ImportGta5Mesh)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportGta5Mesh)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
