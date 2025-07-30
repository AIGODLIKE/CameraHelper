from math import tan, radians

import blf
import bpy
from mathutils import Vector

from ..utils import get_operator_bl_idname



def wrap_blf_size(font_id: int, size):
    if bpy.app.version >= (4, 0, 0):
        blf.size(font_id, size)
    else:
        blf.size(font_id, size, 72)


def view3d_camera_border(scene: bpy.types.Scene, region: bpy.types.Region, rv3d: bpy.types.RegionView3D) -> list[
    Vector]:
    obj = scene.camera
    cam = obj.data

    frame = cam.view_frame(scene=scene)

    # move from object-space into world-space
    frame = [obj.matrix_world @ v for v in frame]

    # move into pixelspace
    from bpy_extras.view3d_utils import location_3d_to_region_2d
    frame_px = [location_3d_to_region_2d(region, rv3d, v) for v in frame]
    return frame_px


def draw_lens_callback(self, context):
    font_id = 0

    area = context.area
    r3d = area.spaces[0].region_3d

    frame_px = view3d_camera_border(context.scene, area, r3d)

    px = frame_px[1]  # bottom right
    x = px[0]
    y = px[1]
    ui_scale = bpy.context.preferences.system.dpi * 1 / 72
    wrap_blf_size(font_id, 30 * ui_scale)
    text_width, text_height = blf.dimensions(font_id, f"{int(context.scene.camera.data.lens)} mm")
    x = x - text_width - 10 * ui_scale
    y = y + int(text_height) - 10 * ui_scale

    blf.position(font_id, x, y, 0)
    blf.color(font_id, 1, 1, 1, 0.5)
    blf.draw(font_id, f"{int(context.scene.camera.data.lens)} mm")


class Cam:
    """
    相机实用类
    """

    def __init__(self, cam):
        self.cam = cam
        self.startLocation = cam.location.copy()
        self.startAngle = cam.data.angle

    def restore(self):
        self.cam.location = self.startLocation.copy()
        self.cam.data.angle = self.startAngle

    def limit_angle_range(self, value):
        max_view_radian = 3.0  # 172d
        min_view_radian = 0.007  # 0.367d
        self.cam.data.angle = max(min(self.cam.data.angle + value, max_view_radian), min_view_radian)

    def get_angle(self) -> float:
        return self.cam.data.angle

    def offsetLocation(self, localCorrectionVector):
        self.cam.location = self.cam.location + (localCorrectionVector @ self.cam.matrix_world.inverted())

    def get_local_point(self, point) -> Vector:
        return self.cam.matrix_world.inverted() @ point


class AdjustCameraLens(bpy.types.Operator):
    """Use Cursor to Adjust Camera Lens"""
    bl_idname = get_operator_bl_idname("adjust_camera_lens")
    bl_label = "Adjust Camera Lens"
    bl_options = {'GRAB_CURSOR', 'BLOCKING', 'UNDO'}

    _handle = None
    mouse_pos = None

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.scene.camera is not None

    def append_handles(self):
        self.cursor_set = True
        bpy.context.window.cursor_modal_set('MOVE_X')
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_lens_callback, (self, bpy.context), 'WINDOW',
                                                              'POST_PIXEL')
        bpy.context.window_manager.modal_handler_add(self)

    def remove_handles(self):
        bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
        bpy.context.window.cursor_modal_restore()

    def adjust_lens(self, angleOffset):
        # limit angle range
        self.camera.limit_angle_range(angleOffset)
        current_angle = self.camera.get_angle()

        scale = self.fovTan / tan(current_angle * 0.5)

        correctionOffset = self.startLocalCursorZ * (1.0 - scale)

        self.camera.offsetLocation(Vector((0.0, 0.0, correctionOffset)))

    def modal(self, context, event):
        self.mouse_pos = event.mouse_region_x, event.mouse_region_y

        if event.type == 'MOUSEMOVE':
            self.mouseDX = self.mouseDX - event.mouse_x
            # shift 减速
            multiplier = 0.01 if event.shift else 0.1

            self.startLocalCursorZ = self.camera.get_local_point(self.cursorLocation)[2]
            self.fovTan = tan(self.camera.get_angle() * 0.5)

            offset = self.mouseDX
            self.adjust_lens(radians(-offset * multiplier))
            # 重置
            self.mouseDX = event.mouse_x

        elif event.type == 'LEFTMOUSE':
            self.remove_handles()
            self.report({"INFO"}, f"{context.scene.camera.name}: {int(context.scene.camera.data.lens)}mm")
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.camera.restore()
            self.remove_handles()
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.mouse_pos = [0, 0]
        # 确认游标在视野内
        cam = context.scene.camera
        localCursor = cam.matrix_world.inverted() @ context.scene.cursor.location
        if localCursor[2] > 0:
            self.report({'WARNING'}, 'Place the 3D cursor in your view')
            return {'CANCELLED'}
        # 初始化参数
        self.camera = Cam(cam)
        self.mouseDX = event.mouse_x
        self.cursorLocation = context.scene.cursor.location
        # add handles
        self.append_handles()
        return {'RUNNING_MODAL'}
