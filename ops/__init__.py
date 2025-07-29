import bpy
from .add_camera import CAMHP_OT_add_view_cam
from .lock_camera import CAMHP_OT_lock_cam

register_class, unregister_class = bpy.utils.register_classes_factory((
    CAMHP_OT_add_view_cam,
    CAMHP_OT_lock_cam,
))


def register():
    ...


def unregister():
    ...
