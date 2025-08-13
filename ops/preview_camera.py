import bpy
import gpu
from gpu_extras.presets import draw_texture_2d
from mathutils import Vector

from ..utils import get_operator_bl_idname, get_camera


class CameraThumbnails:
    """Camera Thumbnails\nLeft Click: Enable\nCtrl: Pin Selected Camera\nCtrl Shift Click: Send to Viewer"""

    camera_data = {
        # area:{
        # camera_name:str,
        # camera_size:float,
        # offset:Vector
        # pin:bool,
        # texture:gpu.types.GPUOffScreen
        # }
    }

    @classmethod
    def pin_selected_camera(cls, context, camera: bpy.types.Camera):
        data = cls.camera_data
        area_hash = hash(context.area)
        if area_hash not in data:
            cls.switch_preview(context, camera)

        data[area_hash]["pin"] = data[area_hash]["pin"] ^ True

    @classmethod
    def switch_preview(cls, context, camera: bpy.types.Camera):
        data = cls.camera_data
        area_hash = hash(context.area)
        if area_hash in data:
            data[area_hash]["enabled"] = data[area_hash]["enabled"] ^ True
            # data.pop(area_hash)
        else:
            data[area_hash] = {
                "camera_name": camera.name,
                "camera_size": 1.0,
                "offset": Vector((0, 0)),
                "pin": False,
                "enabled": True,
            }

    @classmethod
    def update_camera_texture(cls, context):
        print("update_camera_texture")
        scene = context.scene
        WIDTH = 512
        HEIGHT = 256
        if scene.camera:
            cn = scene.camera.name
            if cn not in cls.camera_data:
                offscreen = gpu.types.GPUOffScreen(WIDTH, HEIGHT)
            else:
                offscreen = cls.camera_data[cn]
            view_matrix = scene.camera.matrix_world.inverted()
            projection_matrix = scene.camera.calc_matrix_camera(
                context.evaluated_depsgraph_get(),
                x=WIDTH,
                y=HEIGHT,
            )
            offscreen.draw_view3d(
                scene,
                context.view_layer,
                context.space_data,
                context.region,
                view_matrix,
                projection_matrix,
                do_color_management=False)
            cls.camera_data[cn] = offscreen

    @classmethod
    def draw_texture(cls, context):
        scene = context.scene
        if scene.camera and scene.camera.name in cls.camera_data and cls.check_is_draw(context):
            offscreen = cls.camera_data[scene.camera.name]
            WIDTH = 512
            HEIGHT = 256
            draw_texture_2d(offscreen.texture_color, (10, 10), WIDTH, HEIGHT)

    @classmethod
    def check_is_draw(cls, context):
        area_hash = hash(context.area)
        if area_hash in cls.camera_data:
            return cls.camera_data[area_hash]["enabled"]
        return False

    @classmethod
    def check_is_pin(cls, context):
        area_hash = hash(context.area)
        return area_hash in cls.camera_data and cls.camera_data[area_hash].get("pin", False)

    @classmethod
    def update_2d_button_color(cls, context, gizmo):
        if cls.check_is_draw(context):
            gizmo.color = 0.08, 0.6, 0.08
            gizmo.color_highlight = 0.28, 0.8, 0.28
            if cls.check_is_pin(context):
                gizmo.color = 0.8, 0.2, 0.2
                gizmo.color_highlight = 1, 0.2, 0.2
        else:
            gizmo.color = 0.08, 0.08, 0.08
            gizmo.color_highlight = 0.28, 0.28, 0.28


class PreviewCamera(bpy.types.Operator):
    """Camera Thumbnails\nLeft Click: Enable\nCtrl: Pin Selected Camera\nCtrl Shift Click: Send to Viewer"""
    bl_idname = get_operator_bl_idname("preview_camera")
    bl_label = "Preview Camera"

    check_data = {}
    camera_data = {}

    @classmethod
    def poll(cls, context):
        return context.space_data.type == "VIEW_3D"

    def invoke(self, context, event):
        CameraThumbnails.update_camera_texture(context)
        camera = get_camera(context)
        if event.type == "LEFTMOUSE":
            if event.shift and event.ctrl:
                bpy.ops.camhp.pv_snap_shot()
            elif event.ctrl:
                CameraThumbnails.pin_selected_camera(context, camera)
            else:
                CameraThumbnails.switch_preview(context, camera)
        context.area.tag_redraw()
        return {"FINISHED"}
