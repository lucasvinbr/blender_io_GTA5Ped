import bpy
import bmesh
from mathutils import *



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
    duplicateFaces = 0
    for i in range(0, len(geometry.indices), 3):
        try:
            addedFaces.append(bm.faces.new(addedVerts[j] for j in geometry.indices[i:i+3]))
        except ValueError:
            duplicateFaces += 1
        
    # uv coords
    uvlayer = bm.loops.layers.uv.verify()
    for face in addedFaces:
        for loop in face.loops:
            # Get the index of the vertex the loop contains.
            loop[uvlayer].uv = geometry.uvCoords[loop.vert.index]
        
    bm.faces.ensure_lookup_table()

    #bone weights
    deformlayer = bm.verts.layers.deform.verify()
    for i, vert in enumerate(bm.verts):
        for j in range(4):
            if geometry.boneWeights[i][j] > 0.0:
                vgroup = None
                if meshObj.vertex_groups.find(geometry.boneIndexes[i][j]) == -1:
                    vgroup = meshObj.vertex_groups.new(name = geometry.boneIndexes[i][j])
                else:
                    vgroup = meshObj.vertex_groups[geometry.boneIndexes[i][j]]

                vert[deformlayer][vgroup.index] = geometry.boneWeights[i][j]
    
    #finally, add the bmesh to the actual mesh
    bm.to_mesh(mesh)
    bm.free()

    geometry.mesh = mesh
    geometry.meshObj = meshObj

    print("Built mesh: {} ({} duplicate faces were found and skipped)".format(geometry.meshObj.name, duplicateFaces))
    # print("Mesh bounds: {}".format(geometry.calculate_geometry_bounds()))


def join_geometries_sharing_mats(geometries):
    """returns a list of the "unified" geometries"""
    matIndexesUsed = []

    joinedGeoms = []
    
    for geometry in geometries:
        if matIndexesUsed.count(geometry.shaderIndex) == 0:
            matIndexesUsed.append(geometry.shaderIndex)
            
    for matIndex in matIndexesUsed:
        joinedGeoms.append(join_geometries_with_matindex(geometries, matIndex))

    return joinedGeoms


def join_geometries_with_matindex(geometries, matIndex):
    """returns the "base geometry", the one that should contain the others sharing the same matIndex"""
    baseGeom = None
    geomsToJoin = []
    
    for geometry in geometries:
        if geometry.shaderIndex == matIndex:
            if baseGeom is None:
                baseGeom = geometry
            geomsToJoin.append(geometry)
    
    if(len(geomsToJoin) > 1):
        #join!
        contextOverride = {}
        contextOverride["object"] = contextOverride["active_object"] = baseGeom.meshObj
        contextOverride["selected_objects"] = contextOverride["selected_editable_objects"] = [g.meshObj for g in geomsToJoin]
        bpy.ops.object.join(contextOverride)

    return baseGeom


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
        self.mesh = None
        self.meshObj = None
        self.vertPositions = []
        self.vertNormals = []
        self.shaderIndex = 0
        self.indices = []
        self.uvCoords = []
        self.boneIndexes = []
        self.boneWeights = []
        self.bounds = None

    def calculate_geometry_bounds(self):
        """fills this geometry's 'bounds' variable; also returns it"""
        minBounds = Vector()
        maxBounds = Vector()

        for vertPos in self.vertPositions:
            for i in range(3):
                if minBounds[i] > vertPos[i]:
                    minBounds[i] = vertPos[i]
                
                if maxBounds[i] < vertPos[i]:
                    maxBounds[i] = vertPos[i]


        self.bounds = { 'max' : maxBounds, 'min' : minBounds }

        return self.bounds