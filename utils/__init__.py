import bpy

from .. import __package__ as base_name


def get_pref():
    """get preferences of this addon"""
    return bpy.context.preferences.addons[base_name].preferences


def get_operator_bl_idname(suffix: str) -> str:
    return f"camera_helper.{suffix}"


def get_menu_bl_idname(suffix: str) -> str:
    return f"CAMERA_HELPER_MT_{suffix}"


def get_panel_bl_idname(suffix: str) -> str:
    return f"CAMERA_HELPER_PT_{suffix}"


def get_camera(context) -> "None | bpy.types.Camera":
    if context.object and context.object.type == "CAMERA":
        return context.object
    for obj in context.selected_objects:
        if obj.type == "CAMERA":
            return obj
    for obj in context.scene.objects:
        if obj.type == "CAMERA":
            return obj
    if context.scene.camera:
        return context.scene.camera
    return None
