import bpy

from .add_camera import AddCamera
from .adjust_camera_lens import AdjustCameraLens
from .preview_camera import PreviewCamera
from .snap_shot import SnapShot
from .switch_camera import SwitchCamera

register_class, unregister_class = bpy.utils.register_classes_factory((
    AddCamera,
    PreviewCamera,
    AdjustCameraLens,

    SnapShot,
    SwitchCamera,
))


def register():
    register_class()


def unregister():
    unregister_class()
