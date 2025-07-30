import bpy

from .button_2d import Button2DGizmos
from .preview_camera import PreviewCameraGizmos, PreviewCamera

register_class, unregister_class = bpy.utils.register_classes_factory([
    Button2DGizmos,

    PreviewCamera,
    PreviewCameraGizmos,
])


def register():
    register_class()


def unregister():
    unregister_class()
