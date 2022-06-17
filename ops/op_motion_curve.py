import bpy

bpy.ops.object.paths_calculate(display_type='RANGE', range='SCENE')

bpy.ops.object.paths_clear(only_selected=True)
