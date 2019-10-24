import bpy
import os.path
import traceback
import bmesh
from mathutils import *



def read_mesh_file(context, filepath, use_some_setting):
    meshname = os.path.splitext(os.path.basename(filepath))[0]
    print("Import GTAV Mesh {} : begin".format(meshname))
    with open(filepath, 'r', encoding='utf-8') as reader:
        string_to_mesh(reader, meshname)

    return {'FINISHED'}

def read_until_line_containing(reader, targetStr):
    line = reader.readline()
    
    while targetStr not in line and line != '':
        line = reader.readline()
        
    return line
        

def string_to_mesh(reader, meshName):
    #"Version" header
    line = read_until_line_containing(reader,"Version 165 32")
    
    if line == '':
        return
    
    print("Version OK")
    

    line = read_until_line_containing(reader,"Geometries")
    
    if line == '':
        return
    
    #jump to the line opening brackets, then to the next one, where we presume the first vert is
    line = read_until_line_containing(reader,"{")
    
    if line == '':
        return
    
    print("Reading Geometries Data...")
    
        
    try:
        geometries = read_geometries(reader, line)        
    except Exception as e:
        print("Geometry parsing failed! {}.{}".format(e, traceback.format_exc()))
        
    else:
        #bpy.ops.object.mode_set(mode="OBJECT")
        for geometry in geometries:
            build_geometry(geometry, meshName)
        
        join_geometries_sharing_mats(geometries)
        
        
              
def join_geometries_sharing_mats(geometries):
    matIndexesUsed = []
    
    for geometry in geometries:
        if matIndexesUsed.count(geometry.shaderIndex) == 0:
            matIndexesUsed.append(geometry.shaderIndex)
            
    for matIndex in matIndexesUsed:
        join_geometries_with_matindex(geometries, matIndex)
        
def join_geometries_with_matindex(geometries, matIndex):
    baseGeom = None
    geomsToJoin = []
    
    for geometry in geometries:
        if geometry.shaderIndex == matIndex:
            if baseGeom is None:
                baseGeom = geometry
            geomsToJoin.append(geometry)
    
    contextOvr = {}
    contextOvr["object"] = contextOvr["active_object"] = baseGeom.meshObj
    contextOvr["selected_objects"] = contextOvr["selected_editable_objects"] = [g.meshObj for g in geomsToJoin]
    
    bpy.ops.object.join(contextOvr)


def build_geometry(geometry, meshName):
    """uses the stored geometry data to build the mesh"""
    print("Building Geometry...")
    
    mesh, meshObj = create_mesh(meshName)
    
    bm = bmesh.new()
    
    addedVerts = []
    
    #add verts...
    for i, vertPos in enumerate(geometry.vertPositions):
        newVert = bm.verts.new(vertPos)
        newVert.normal = geometry.vertNormals[i]
        addedVerts.append(newVert)
    
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    
    #faces
    addedFaces = []
    
    for i in range(0, len(geometry.indices), 3):
        addedFaces.append(bm.faces.new(addedVerts[j] for j in geometry.indices[i:i+3]))
        
    # uv coords
    uvlayer = bm.loops.layers.uv.verify()
    for face in addedFaces:
        for loop in face.loops:
            # Get the index of the vertex the loop contains.
            loop[uvlayer].uv = geometry.uvCoords[loop.vert.index]
        
    bm.faces.ensure_lookup_table()
    
    #finally, add the bmesh to the actual mesh
    bm.to_mesh(mesh)
    bm.free()
    
    geometry.mesh = mesh
    geometry.meshObj = meshObj
    

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
    
    geomData = GeometryData()
    
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
    
    #normals
    lineDataEntry = lineData[3].strip().split(" ")
    geomData.vertNormals.append(Vector(map(float,lineDataEntry)))
    
    #uvs (they are flipped!)
    lineDataEntry = Vector(map(float, lineData[6].strip().split(" ")))
    lineDataEntry.y *= -1
    
    geomData.uvCoords.append(lineDataEntry)
    
    return line
    
    
def create_mesh(meshName):
    """Creates a mesh object and adds it to the current collection"""
    mesh = bpy.data.meshes.new(meshName)
    meshObj = bpy.data.objects.new(meshName, mesh)
    
    bpy.context.scene.collection.objects.link(meshObj)
    
    return mesh, meshObj

def delete_mesh(mesh):
    """Deletes the target mesh (mesh obj will also be deleted)"""
    bpy.data.meshes.remove(mesh)
    
class GeometryData():
    
    def __init__(self):
        self.vertPositions = []
        self.vertNormals = []
        self.shaderIndex = 0
        self.indices = []
        self.uvCoords = []
