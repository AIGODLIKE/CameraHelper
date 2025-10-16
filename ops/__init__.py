import bpy

from .add_camera import AddCamera
from .adjust_camera_lens import AdjustCameraLens
from .preview_camera import PreviewCamera
from .snapshot import Snapshot
from .switch_camera import SwitchCamera
from . import motion
register_class, unregister_class = bpy.utils.register_classes_factory((
    AddCamera,
    PreviewCamera,
    AdjustCameraLens,

    Snapshot,
    SwitchCamera,
))


def register():
    register_class()
    motion.register()

def unregister():
    unregister_class()
    motion.unregister()
