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
    if hasattr(context, "object") and context.object and context.object.type == "CAMERA":
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


def get_camera_preview_size(context):
    pref = get_pref()
    max_height = pref.camera_thumb.max_width
    max_width = pref.camera_thumb.max_height
    height = max_height
    ratio = context.scene.render.resolution_x / context.scene.render.resolution_y
    width = int(height * ratio)
    if width > max_width:
        width = max_width
        height = int(width / ratio)
    return width, height
