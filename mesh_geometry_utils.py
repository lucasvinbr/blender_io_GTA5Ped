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


def meshobj_to_geometries(meshObj, parentSkeleton):
    """returns a list of GeometryData objects, one per material, containing the meshObj's relevant data"""
    #make sure there's only one selected object, because we're going to duplicate it
    if len(bpy.context.selected_objects) > 0:
        bpy.ops.object.select_all()
    
    meshObj.select_set(True)
    #also make sure it's the active one
    bpy.context.view_layer.objects.active = meshObj

    #duplicating in these conditions should make the clone be the only one selected and active
    bpy.ops.object.duplicate()

    objCopy = bpy.context.active_object

    #limit weights to 4 per vertex and normalize them
    bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL')

    bpy.ops.object.mode_set( mode = 'EDIT' )

    #separate and mark each object with its "shaderIndex"
    #but keep the last piece in this object, so that we don't end up with an extra empty geometry
    for i in range(len(objCopy.material_slots) - 1, 0, -1):
        objCopy.active_material_index = i
        objCopy["Gta5MatIndex"] = i
        bpy.ops.object.material_slot_select()
        bpy.ops.mesh.separate()

    objCopy["Gta5MatIndex"] = 0

    resultingGeometries = []

    #after separating, all pieces are selected
    for obj in bpy.context.selected_objects:
        resultingGeometries.append(parse_obj_to_geometrydata(obj, parentSkeleton, obj["Gta5MatIndex"]))

    #delete duplicates now
    for obj in bpy.context.selected_objects:
        delete_mesh(obj.data)

    return resultingGeometries


def parse_obj_to_geometrydata(meshObj, parentSkeleton, shaderIndex):
    """parses a single-material mesh into a GeometryData object"""
    geom = GeometryData()

    bm = bmesh.new()
    bm.from_mesh(meshObj.data)

    geom.shaderIndex = shaderIndex

    deformlayer = bm.verts.layers.deform.verify()

    skelData = None

    if parentSkeleton is not None:
        skelData = parentSkeleton.data
    
    boneIndexTranslation = {} #vertex group index to skeleton bone index



    #vert positions and normals...
    for vert in bm.verts:
        geom.vertPositions.append(vert.co.copy())
        geom.vertNormals.append(vert.normal.copy())

        #weights...
        if skelData is not None:
            vertBoneIndexes = []
            vertBoneWeights = []
            for groupIndex, weight in vert[deformlayer].items():
                if boneIndexTranslation.get(groupIndex, -1) == -1:
                    boneIndexTranslation[groupIndex] = skelData.bones.find(meshObj.vertex_groups[groupIndex].name)
                
                vertBoneIndexes.append(boneIndexTranslation[groupIndex])
                vertBoneWeights.append(weight)

            #if this vert has less than 4 bones with weights, pad the indexes and weights lists with empty entries
            vertBoneIndexes += [0] * (4 - len(vertBoneIndexes))
            vertBoneWeights += [0.0] * (4 - len(vertBoneWeights))

            geom.boneIndexes.append(vertBoneIndexes)
            geom.boneWeights.append(vertBoneWeights)

        else:
            geom.boneIndexes.append([0] * 4)
            geom.boneWeights.append([0.0] * 4)
        
            
    uvlayer = bm.loops.layers.uv.verify()
    #fill uvCoords with blank entries so that we can fill them in any order
    geom.uvCoords = [0] * len(geom.vertPositions)

    #indices and uv
    for face in bm.faces:
        for vert in face.verts:
            geom.indices.append(vert.index)
        for loop in face.loops:
            print("index {}".format(loop.vert.index))
            print("before {}".format(geom.uvCoords[loop.vert.index]))
            geom.uvCoords[loop.vert.index] = loop[uvlayer].uv.copy()
            geom.uvCoords[loop.vert.index].y *= -1
            print("after {}".format(geom.uvCoords[loop.vert.index]))
                

    #finally, calculate and store bounds
    geom.calculate_geometry_bounds()
    # print("geom {}".format(geom.indices))

    bm.free()

    return geom


class GeometryData():
    """class representing most of the data stored in a .mesh file, especially in the 'Geometry' sections"""
    def __init__(self):
        self.mesh = None
        self.meshObj = None
        self.vertPositions = [] #list of vectors
        self.vertNormals = [] #list of vectors
        self.shaderIndex = 0
        self.indices = [] #list of ints - vertex indices, in the winding order, in order to make faces
        self.uvCoords = [] #list of vectors (y axis is flipped, apparently)
        self.boneIndexes = [] #list of lists, each inner list having 4 ints
        self.boneWeights = [] #list of lists, each inner list having 4 floats
        self.bounds = None #dict with 'max' and 'min' vectors

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