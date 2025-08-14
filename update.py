import bpy
from bpy.app.handlers import persistent


@persistent
def depsgraph_update_post(scene, depsgraph):
    from .ops.preview_camera import CameraThumbnails
    CameraThumbnails.update()


def register():
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_post)


def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_post)
