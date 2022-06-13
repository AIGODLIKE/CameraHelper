import bpy
import blf

from bpy.types import Operator
from bpy.props import EnumProperty, StringProperty

from mathutils import Vector
from math import tan, radians, sqrt


class CAMHP_OT_move_view_between_cams(Operator):
    bl_idname = 'camhp.move_view_between_cams'
    bl_label = 'Move View Between Cameras'
    bl_options = {"INTERNAL"}

    r3d = None  # 当前region

    # camera
    tg_cam: StringProperty()  # pass in
    tg_loc = None
    tg_quat = None

    ori_view_distance = None
    ori_view_location = None
    ori_view_rotation = None
    ori_view_lens = None
    # 动画控制
    anim_fac = 0  # 动画比例 0~1
    anim_iter = 60  # 动画更新 秒
    anim_time = 0.5  # 持续时间 秒
    anim_out = 0.4  # 退出动画比例

    _timer = None

    @classmethod
    def poll(self, context):
        return context.area.type == 'VIEW_3D'

    def remove_handle(self):
        # bpy.types.SpaceNodeEditor.draw_handler_remove(self._handle, 'WINDOW')
        bpy.context.window_manager.event_timer_remove(self._timer)
        bpy.context.window_manager.mathp_node_anim = False

    def append_handle(self):
        self._timer = bpy.context.window_manager.event_timer_add(self.anim_time / self.anim_iter,
                                                                 window=bpy.context.window)  # 添加计时器检测状态
        args = (self, bpy.context)
        # self._handle = bpy.types.SpaceNodeEditor.draw_handler_add(draw_process_callback_px, args, 'WINDOW',
        #                                                           'POST_PIXEL')
        bpy.context.window_manager.modal_handler_add(self)
        bpy.context.window_manager.mathp_node_anim = True

    def offset_view(self, anim_fac):
        fac = anim_fac
        cam = bpy.context.scene.camera.data

        offset_loc = self.ori_view_location.lerp(self.tg_loc, fac)
        offset_rot = self.ori_view_rotation.slerp(self.tg_quat, fac)
        offset_alpha = self.ori_passepartout_alpha * fac

        self.r3d.view_location = offset_loc
        self.r3d.view_rotation = offset_rot

        bpy.context.space_data.lens = self.ori_view_lens[0] + (
                cam.lens - self.ori_view_lens[0]) * fac / self.anim_out  # 加快
        cam.passepartout_alpha = offset_alpha

    def correct_offset(self):
        """ 用于最终位置矫正

        :return:
        """
        # correct
        self.r3d.view_location = self.tg_loc
        self.r3d.view_rotation = self.tg_quat
        self.r3d.view_camera_zoom = 0
        self.r3d.view_perspective = 'CAMERA'
        bpy.context.space_data.lens = bpy.context.scene.camera.data.lens
        # bpy.ops.view3d.view_camera("INVOKE_DEFAULT")

    def restore(self):
        """ 复位，恢复用户的选择距离和视口位置

        :return:
        """
        self.r3d.view_distance = 6
        # self.r3d.view_distance = self.ori_view_distance[0]
        # self.r3d.view_location = self.ori_view_location
        # self.r3d.view_rotation = self.ori_view_rotation
        bpy.context.space_data.lens = self.ori_view_lens[0]
        bpy.context.scene.camera.data.passepartout_alpha = self.ori_passepartout_alpha

    def invoke(self, context, event):
        area = context.area
        self.r3d = area.spaces[0].region_3d
        tg = bpy.data.objects[self.tg_cam]

        self.tg_loc = tg.matrix_world.to_translation().copy()
        self.tg_quat = tg.matrix_world.to_quaternion().copy()

        self.ori_passepartout_alpha = tg.data.passepartout_alpha
        self.ori_view_distance = (self.r3d.view_distance,)  # 放入元组防止变化
        self.ori_view_location = self.r3d.view_location
        self.ori_view_rotation = self.r3d.view_rotation
        self.ori_view_lens = (getattr(context.space_data, "lens"),)  # 放入元组防止变化

        self.append_handle()
        # 进入一般界面, 设置相机
        self.r3d.view_distance = 0
        self.r3d.view_perspective = 'PERSP'
        context.scene.camera = bpy.data.objects[self.tg_cam]

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        context.region.tag_redraw()

        if event.type == 'TIMER':
            if self.anim_fac >= self.anim_out:  # 加快进入
                self.remove_handle()
                # 强制对齐
                self.correct_offset()
                self.restore()
                return {'FINISHED'}
            # 移动动画
            self.offset_view(self.anim_fac)
            self.anim_fac += 1 / (self.anim_iter + 1)  # last delay

        return {"PASS_THROUGH"}


class CAMHP_OT_switch_cam(Operator):
    """Switch Camera"""
    bl_idname = 'camhp.switch_cam'
    bl_label = 'Switch Camera'
    bl_property = 'enum_cam'

    _enum_cams = []  # 储存数据

    def get_cameras(self, context):
        enum_items = CAMHP_OT_switch_cam._enum_cams
        enum_items.clear()

        for i, obj in enumerate(bpy.data.objects):
            if obj.type != 'CAMERA': continue

            if obj is context.scene.camera:
                enum_items.insert(0, (obj.name, obj.name, '', 'VIEW_CAMERA', i))
            else:
                enum_items.append((obj.name, obj.name, '', 'DOT', i))

        return enum_items

    enum_cam: EnumProperty(
        name="Camera",
        items=get_cameras,
    )

    def execute(self, context):
        if self.enum_cam != context.scene.camera.name:
            bpy.ops.camhp.move_view_between_cams('INVOKE_DEFAULT', tg_cam=self.enum_cam)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class CAMHP_OT_add_view_cam(Operator):
    """Add View Camera"""
    bl_idname = 'camhp.add_view_cam'
    bl_label = 'Add View Camera'

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def execute(self, context):
        # 创建相机
        cam_data = bpy.data.cameras.new(name='Camera')
        cam = bpy.data.objects.new('Camera', cam_data)
        context.collection.objects.link(cam)
        # 设置
        cam.data.show_name = True
        # 进入视图
        context.scene.camera = cam
        bpy.ops.view3d.camera_to_view()

        area = context.area
        r3d = area.spaces[0].region_3d
        r3d.view_camera_zoom = 0

        context.region.tag_redraw()

        return {"FINISHED"}


class CAMHP_OT_lock_cam(Operator):
    """Camera to View"""
    bl_idname = 'camhp.lock_cam'
    bl_label = 'Lock View'

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D' and context.scene.camera:
            return context.area.spaces[0].region_3d.view_perspective == 'CAMERA'

    def execute(self, context):
        setattr(context.space_data, "lock_camera", not getattr(context.space_data, "lock_camera"))
        return {'FINISHED'}


class Cam():
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

    def get_angle(self):
        return self.cam.data.angle

    def offsetLocation(self, localCorrectionVector):
        self.cam.location = self.cam.location + (localCorrectionVector @ self.cam.matrix_world.inverted())

    def get_local_point(self, point):
        return self.cam.matrix_world.inverted() @ point

def wonk(fac):
    return 50*(2*sqrt(fac) - sqrt(2))

def draw_lens_callback(self, context):
    font_id = 0

    area = context.area
    r3d = area.spaces[0].region_3d
    scale = r3d.view_camera_zoom

    region = context.region

    c_x = region.width / 2
    c_y = region.height / 2
    x = region.width - 160
    y = 80

    # 侧面面板偏移
    for r in context.area.regions:
        if r.type == 'UI':
            x -= r.width
            break

    blf.size(font_id, 20, 120)
    blf.position(font_id, x, y, 0)
    blf.color(font_id, 1, 1, 1, 0.5)
    blf.draw(font_id, f"{int(context.scene.camera.data.lens)} mm")


class CAMHP_OT_adjust_cam_lens(Operator):
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


def register():
    bpy.utils.register_class(CAMHP_OT_move_view_between_cams)
    bpy.utils.register_class(CAMHP_OT_switch_cam)
    bpy.utils.register_class(CAMHP_OT_add_view_cam)
    bpy.utils.register_class(CAMHP_OT_lock_cam)
    bpy.utils.register_class(CAMHP_OT_adjust_cam_lens)


def unregister():
    bpy.utils.unregister_class(CAMHP_OT_move_view_between_cams)
    bpy.utils.unregister_class(CAMHP_OT_switch_cam)
    bpy.utils.unregister_class(CAMHP_OT_add_view_cam)
    bpy.utils.unregister_class(CAMHP_OT_lock_cam)
    bpy.utils.unregister_class(CAMHP_OT_adjust_cam_lens)
