import bpy

from .button_2d import Button2DGizmos
from .motion_move import MotionCameraAdjustGizmo, MotionCameraAdjustGizmos
from .preview_camera import PreviewCameraGizmos, PreviewCameraAreaGizmo

classes = (
    Button2DGizmos,

    PreviewCameraAreaGizmo,
    PreviewCameraGizmos,

    MotionCameraAdjustGizmo,
    MotionCameraAdjustGizmos,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes)


def register():
    register_class()


def unregister():
    unregister_class()
