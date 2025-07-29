import bpy

from .button_2d import Button2DGizmos

register_class, unregister_class = bpy.utils.register_classes_factory([
    Button2DGizmos,
])


def register():
    register_class()


def unregister():
    unregister_class()
