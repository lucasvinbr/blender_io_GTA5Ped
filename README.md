# blender_io_GTA5Ped
import-export of parts of OpenIV's openFormats, focused on ped meshes and information contained in ODD and "children" ODR, .mesh and .skel files.

Currently, it can import skeletons (wrongly positioned but working) and meshes, and can export meshes as .mesh files.

It does not look for textures (meshes are imported with UVs though) and doesn't create materials.

Import-export buttons are found at the "File" menu.

A little how-to is in https://github.com/lucasvinbr/blender_io_GTA5Ped/wiki/Getting-a-ped-model-into-GTA5

Installation: use the "install addon" option from blender's user preferences menu. No need to unzip the file!
When upgrading from a previous version, close and reopen blender after reinstalling for the changes to take effect.
