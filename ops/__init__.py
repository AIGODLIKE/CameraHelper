import bpy

from .add_camera import CAMHP_OT_add_view_cam
from .lock_camera import CAMHP_OT_lock_cam
from .preview_camera import CAMHP_OT_campv_popup
from .adjust_cam_lens import CAMHP_OT_adjust_cam_lens

register_class, unregister_class = bpy.utils.register_classes_factory((
    CAMHP_OT_add_view_cam,
    CAMHP_OT_lock_cam,
    CAMHP_OT_campv_popup,
    CAMHP_OT_adjust_cam_lens,
))


def register():
    register_class()


def unregister():
    unregister_class()
