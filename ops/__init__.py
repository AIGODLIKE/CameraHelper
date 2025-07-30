import bpy

from .add_camera import AddCamera
from .lock_camera import CAMHP_OT_lock_cam
from .preview_camera import PreviewCamera
from .adjust_camera_lens import AdjustCameraLens

register_class, unregister_class = bpy.utils.register_classes_factory((
    AddCamera,
    CAMHP_OT_lock_cam,
    PreviewCamera,
    AdjustCameraLens,
))


def register():
    register_class()


def unregister():
    unregister_class()
