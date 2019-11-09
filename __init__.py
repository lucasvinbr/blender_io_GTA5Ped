# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name" : "io_GTA5Ped",
    "author" : "lucasvinbr (openFormats and OpenIv by OpenIV team)",
    "description" : "Imports and exports some openFormats ped data",
    "blender" : (2, 80, 0),
    "version" : (0, 0, 1),
    "location" : "",
    "warning" : "",
    "category" : "Generic"
}

import bpy
from . import import_mesh
from . import import_skel
from . import import_odr
from . import import_odd

class GtaIOPanel(bpy.types.Panel):
    """Panel containing import/export options in the Scene tab"""
    bl_label = "GTA5 Ped I/O"
    bl_idname = "SCENE_PT_GTA5_PED"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        pass
        #layout = self.layout
        #curScene = context.scene
        

def register():
    import_mesh.register()
    import_skel.register()
    import_odr.register()
    import_odd.register()

def unregister():
    import_mesh.unregister()
    import_skel.unregister()
    import_odr.unregister()
    import_odd.unregister()
