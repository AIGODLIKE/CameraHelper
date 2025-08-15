import bpy
import numpy as np

from ..utils import get_camera
from ..utils.color import linear_to_srgb


def save_texture_to_image(context, camera, texture):
    camera_name = camera.name

    x = context.scene.render.resolution_x
    y = context.scene.render.resolution_y
    key = f"Snap_Shot_{camera_name}"
    if key in bpy.data.images:
        img = bpy.data.images[key]
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name=key,
                              width=x,
                              height=y)
    try:
        data = np.asarray(texture.read(), dtype=np.uint8)
        image_float = data.astype(np.float32) / 255.0
        image_float = image_float.transpose((2, 1, 0)).ravel()
        img.pixels.foreach_set(linear_to_srgb(image_float))
    except TypeError as e:
        print(e)

    bpy.ops.render.view_show('INVOKE_DEFAULT')
    for area in context.screen.areas:
        if area.type == 'IMAGE_EDITOR':
            for space in area.spaces:
                if space.type == 'IMAGE_EDITOR':
                    space.image = img
                    break
    return key

class SnapShot(bpy.types.Operator):
    """Snap Shot"""
    bl_idname = "camhp.pv_snap_shot"
    bl_label = "Snapshot"

    def invoke(self, context, event):
        from ..camera_thumbnails import CameraThumbnails
        area = context.area
        camera = None

        CameraThumbnails.update()
        if camera_data := CameraThumbnails.get_camera_data(area):
            if camera_name := camera_data.get("camera_name", None):
                camera = context.scene.objects.get(camera_name, None)
        if camera is None:
            camera = get_camera(context)

        if camera:
            space = context.space_data
            ori_show_overlay = space.overlay.show_overlays
            space.overlay.show_overlays = False

            texture = CameraThumbnails.update_camera_texture(context, camera, True)
            save_texture_to_image(context, camera, texture)
            space.overlay.show_overlays = ori_show_overlay

            self.report({'INFO'}, 'Snapshot')
            return {'FINISHED'}
        self.report({'ERROR'}, 'Not find camera')
        return {'CANCELLED'}
