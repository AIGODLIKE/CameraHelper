from math import tan, radians

import bpy

import blf
from mathutils import Vector


def draw_lens_callback(self, context):
    font_id = 0

    area = context.area
    r3d = area.spaces[0].region_3d

    frame_px = view3d_camera_border(context.scene, area, r3d)

    px = frame_px[1]  # bottom right
    x = px[0]
    y = px[1]

    # get text dimensions
    wrap_blf_size(font_id, 30 * ui_scale())
    text_width, text_height = blf.dimensions(font_id, f"{int(context.scene.camera.data.lens)} mm")
    x = x - text_width - 10 * ui_scale()
    y = y + int(text_height) - 10 * ui_scale()

    blf.position(font_id, x, y, 0)
    blf.color(font_id, 1, 1, 1, 0.5)
    blf.draw(font_id, f"{int(context.scene.camera.data.lens)} mm")


class CAMHP_OT_adjust_cam_lens(bpy.types.Operator):
    """Use Cursor to Adjust Camera Lens"""
    bl_idname = "camhp.adjust_cam_lens"
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
