import bpy
import math
from mathutils import Vector, Euler, Matrix
from bpy.types import GizmoGroup, SpaceView3D, PropertyGroup

from .gz_custom import GizmoInfo_2D


class GizmoGroupBase:
    """use_tooltip"""
    bl_label = "View Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', 'SCALE', 'SHOW_MODAL_ALL'}

    VIEW = None

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            vp = context.area.spaces[0].region_3d.view_perspective

            if cls.VIEW == 'CAMERA' and context.scene.camera:
                return vp == cls.VIEW

            elif cls.VIEW == 'PERSP':
                return vp == cls.VIEW

    def draw_prepare(self, context):
        # ui scale
        ui_scale = context.preferences.system.dpi / 72
        region = context.region

        step = 30 * ui_scale
        icon_scale = (80 * 0.35) / 2  # 14
        # 从屏幕右侧起
        start_x = region.width - (icon_scale * ui_scale + step) / 2
        start_y = region.height

        # 检查是否启用区域重叠，若启用则加上宽度以符合侧面板移动
        if context.preferences.system.use_region_overlap:
            for region in context.area.regions:
                if region.type == 'UI':
                    start_x -= region.width
                elif region.type == 'HEADER':
                    start_y -= region.height

        # 检查是否开启坐标轴
        if context.preferences.view.mini_axis_type == 'MINIMAL':
            size = context.preferences.view.mini_axis_size * ui_scale * 2  # 获取实际尺寸 此尺寸需要乘2
            start_y -= size + step * 2  #
        elif context.preferences.view.mini_axis_type == 'GIZMO':
            size = context.preferences.view.gizmo_size_navigate_v3d * ui_scale * 1.2  # 获取实际尺寸 此尺寸需要乘1.2
            start_y -= size + step * 2  #
        elif context.preferences.view.mini_axis_type == 'NONE':
            start_y -= step * 2

            # 检查是否开启默认控件
        if context.preferences.view.show_navigate_ui:
            start_y -= (icon_scale * ui_scale + step) * 3
        else:
            start_y -= step * 2 * ui_scale

        for i, gz in enumerate(self.gizmos):
            gz.matrix_basis[0][3] = start_x
            gz.matrix_basis[1][3] = start_y - step * i
            gz.scale_basis = icon_scale

        context.area.tag_redraw()


class CAMHP_UI_persp_view(GizmoGroupBase, GizmoGroup):
    bl_idname = "CAMHP_UI_persp_view"

    VIEW = 'PERSP'

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_button_2d")
        gz.icon = 'ADD'
        gz.draw_options = {'BACKDROP', 'OUTLINE'}
        gz.use_tooltip = True
        gz.alpha = .8
        gz.color = 0.08, 0.08, 0.08
        gz.color_highlight = 0.28, 0.28, 0.28
        gz.alpha_highlight = 0.8

        gz.scale_basis = (80 * 0.35) / 2  # Same as buttons defined in C

        props = gz.target_set_operator("camhp.add_view_cam")
        self.gz_add_cam = gz

        gz = self.gizmos.new("GIZMO_GT_button_2d")
        gz.use_event_handle_all = True
        gz.icon = 'IMAGE_PLANE'
        gz.draw_options = {'BACKDROP', 'OUTLINE'}
        gz.use_tooltip = True
        gz.alpha = .8
        gz.color = 0.08, 0.08, 0.08
        gz.color_highlight = 0.28, 0.28, 0.28
        gz.alpha_highlight = 0.8

        gz.scale_basis = (80 * 0.35) / 2  # Same as buttons defined in C

        props = gz.target_set_operator("camhp.campv_popup")
        self.gz_cam_pv = gz

    def refresh(self, context):
        if context.window_manager.camhp_pv.enable:
            self.gz_cam_pv.color = 0.08, 0.6, 0.08
            self.gz_cam_pv.color_highlight = 0.28, 0.8, 0.28

            if context.window_manager.camhp_pv.pin:
                self.gz_cam_pv.color = 0.8, 0.2, 0.2
                self.gz_cam_pv.color_highlight = 1, 0.2, 0.2
        else:
            self.gz_cam_pv.color = 0.08, 0.08, 0.08
            self.gz_cam_pv.color_highlight = 0.28, 0.28, 0.28

        context.area.tag_redraw()


class CAMHP_UI_cam_view(GizmoGroupBase, GizmoGroup):
    bl_idname = "CAMHP_UI_cam_view"

    VIEW = 'CAMERA'

    def refresh(self, context):
        self.set_gz_lock(context)
        context.area.tag_redraw()

    def set_gz_lock(self, context):
        """用于更新gz_lock的图标

        :param context:
        :return:
        """
        icon = 'LOCKED' if context.space_data.lock_camera else 'UNLOCKED'
        if self.gz_lock.icon != icon:
            self.gizmos.remove(self.gz_lock)
            self.add_gz_lock(context)

    def add_gz_lock(self, context):
        icon = 'LOCKED' if context.space_data.lock_camera else 'UNLOCKED'
        gz = self.gizmos.new("GIZMO_GT_button_2d")
        gz.icon = icon
        gz.draw_options = {'BACKDROP', 'OUTLINE'}
        gz.use_tooltip = True
        gz.alpha = .8
        gz.color = (0.8, 0.2, 0.2) if context.space_data.lock_camera else (0.08, 0.08, 0.08)
        gz.color_highlight = (1, 0.2, 0.2) if context.space_data.lock_camera else (0.28, 0.28, 0.28)
        gz.alpha_highlight = 0.8

        gz.scale_basis = (80 * 0.35) / 2  # Same as buttons defined in C
        props = gz.target_set_operator("camhp.lock_cam")
        self.gz_lock = gz

    def setup(self, context):
        # 调整焦距控件
        gz = self.gizmos.new("GIZMO_GT_button_2d")
        gz.icon = 'VIEW_PERSPECTIVE'
        gz.draw_options = {'BACKDROP', 'OUTLINE'}
        gz.use_tooltip = True
        gz.use_draw_modal = True
        gz.alpha = .8
        gz.color = 0.08, 0.08, 0.08
        gz.color_highlight = 0.28, 0.28, 0.28
        gz.alpha_highlight = 0.8

        gz.scale_basis = (80 * 0.35) / 2  # Same as buttons defined in C

        props = gz.target_set_operator("camhp.adjust_cam_lens")
        self.gz_move = gz
        # 切换相机控件
        gz = self.gizmos.new("GIZMO_GT_button_2d")
        gz.icon = 'CAMERA_DATA'
        gz.draw_options = {'BACKDROP', 'OUTLINE'}
        gz.use_tooltip = True
        gz.alpha = .8
        gz.color = 0.08, 0.08, 0.08
        gz.color_highlight = 0.28, 0.28, 0.28
        gz.alpha_highlight = 0.8

        gz.scale_basis = (80 * 0.35) / 2  # Same as buttons defined in C

        props = gz.target_set_operator("camhp.switch_cam")
        self.gz_switch = gz

        # 相机设置
        gz = self.gizmos.new("GIZMO_GT_button_2d")
        gz.icon = 'PROPERTIES'
        gz.draw_options = {'BACKDROP', 'OUTLINE'}
        gz.use_tooltip = True
        gz.alpha = .8
        gz.color = 0.08, 0.08, 0.08
        gz.color_highlight = 0.28, 0.28, 0.28
        gz.alpha_highlight = 0.8

        gz.scale_basis = (80 * 0.35) / 2  # Same as buttons defined in C

        props = gz.target_set_operator("camhp.popup_cam_settings")
        self.gz_setttings = gz

        self.add_gz_lock(context)


from .gz_custom import CAMHP_GT_custom_move_3d, CAMHP_GT_custom_move_1d, CAMHP_GT_custom_rotate_1d
from .gz_custom import CAMHP_OT_insert_keyframe, CAMHP_OT_rotate_object
from ..prefs.get_pref import get_pref


class CAMHP_UI_motion_curve_gz(GizmoGroupBase, GizmoGroup):
    bl_idname = "CAMHP_UI_motion_curve_gz"
    bl_label = "Camera Motion Curve"
    bl_options = {'3D', 'PERSISTENT'}

    _move_gz = dict()
    _rotate_gz = dict()
    _gz_axis = dict()

    cam_list = list()

    @classmethod
    def poll(cls, context):
        ob = context.object
        view = context.space_data
        if (
                ob and
                ob.type in {'CAMERA', 'EMPTY'} and
                view.region_3d.view_perspective != 'CAMERA' and
                not view.region_quadviews
        ):
            return True
        else:
            return False

    def draw_prepare(self, context):
        pass

    def setup(self, context):
        self._move_gz.clear()
        self.gz_motion_cam = None

        self.cam_list = [item.camera for item in context.object.motion_cam.list]

        self.add_motion_cam_gz(context)
        self.draw_prepare(context)

    def add_motion_cam_gz(self, context):
        if self.gz_motion_cam is None:
            gz = self.gizmos.new("CAMHP_GT_custom_move_1d")
            gz.target_set_prop('offset', context.object.motion_cam, 'offset_factor')

            gz._camera = context.object
            gz.use_tooltip = True
            gz.use_event_handle_all = True

            # 设置gizmo的偏好
            pref_gz = get_pref().gz_motion_camera

            gz.alpha = pref_gz.color[3]
            gz.color = pref_gz.color[:3]
            gz.color_highlight = pref_gz.color_highlight[:3]
            gz.alpha_highlight = pref_gz.color_highlight[3]

            gz.use_draw_modal = True
            gz.use_draw_scale = False

            self.gz_motion_cam = gz
        try:
            for gz in self._move_gz.keys():
                self.gizmos.remove(gz)

            for gz in self._rotate_gz.keys():
                self.gizmos.remove(gz)
        except ReferenceError:  # new file open
            pass

        self._move_gz.clear()
        self._rotate_gz.clear()
        self._gz_axis.clear()

        for index, item in enumerate(context.object.motion_cam.list):
            item = context.object.motion_cam.list[index]

            # self.add_move_gz(index, item)
            # print('Add gizmo')
            # TODO 移除gizmo以避免崩溃。 Blender报错：EXCEPTION_ACCESS_VIOLATION，联系官方处理中
            # self.add_rotate_gz(item, 'X')
            # self.add_rotate_gz(item, 'Y')
            # self.add_rotate_gz(item, 'Z')

        self.correct_rotate_gz_euler()

    def correct_rotate_gz_euler(self):
        for gz, axis in self._gz_axis.items():
            if axis == 'X':
                rotate = Euler((math.radians(90), math.radians(-180), math.radians(-90)), 'XYZ')  # 奇怪的数值

            elif axis == 'Y':
                rotate = Euler((math.radians(-90), 0, 0), 'XYZ')

            else:
                rotate = Euler((0, 0, math.radians(90)), 'XYZ')

            cam = self._rotate_gz[gz]
            # print('correct gizmo')
            rotate.rotate(cam.matrix_world.to_euler('XYZ'))
            gz.matrix_basis = rotate.to_matrix().to_4x4()
            gz.matrix_basis.translation = cam.matrix_world.translation

    def add_rotate_gz(self, item, axis='Z'):
        # rotate gz
        # gz = self.gizmos.new("GIZMO_GT_dial_3d")
        gz = self.gizmos.new("CAMHP_GT_custom_rotate_1d")

        prop = gz.target_set_operator(CAMHP_OT_rotate_object.bl_idname)
        prop.obj_name = item.camera.name
        prop.axis = axis

        gz.use_tooltip = True
        gz.use_event_handle_all = True

        gz.use_draw_modal = True
        gz.use_draw_scale = False

        # red, green, blue for X Y Z axis
        gz.alpha = 0.5
        gz.alpha_highlight = 1

        ui = bpy.context.preferences.themes[0].user_interface

        axis_x = ui.axis_x[:3]
        axis_y = ui.axis_y[:3]
        axis_z = ui.axis_z[:3]

        if axis == 'X':
            gz.color = axis_x
        elif axis == 'Y':
            gz.color = axis_y
        elif axis == 'Z':
            gz.color = axis_z

        gz.color_highlight = (1, 1, 1)

        self._rotate_gz[gz] = item.camera
        self._gz_axis[gz] = axis

    def add_move_gz(self, index, item):
        # move gz
        gz = self.gizmos.new("CAMHP_GT_custom_move_3d")
        gz._index = index
        gz._camera = item.camera

        gz.target_set_prop('offset', item.camera, 'location')

        gz.use_tooltip = True
        gz.use_event_handle_all = True

        pref_gz = get_pref().gz_motion_source
        gz.alpha = pref_gz.color[3]
        gz.color = pref_gz.color[:3]
        gz.color_highlight = pref_gz.color_highlight[:3]
        gz.alpha_highlight = pref_gz.color_highlight[3]

        gz.use_draw_modal = True
        gz.use_draw_scale = False

        self._move_gz[gz] = item.camera

    def refresh(self, context):
        # print("CamHp::refresh")
        update_gz = False
        # 添加相机时候自动添加gizmo
        cam_list = [item.camera for item in context.object.motion_cam.list]
        if self.cam_list != cam_list:
            self.cam_list = cam_list
            update_gz = True

        # 切换物体移除gizmo
        if len(context.object.motion_cam.list) == 0:
            if self.gz_motion_cam:
                self.gizmos.remove(self.gz_motion_cam)
                self.gz_motion_cam = None

                for gz in self._move_gz.keys():
                    self.gizmos.remove(gz)

                for gz in self._rotate_gz.keys():
                    # print('remove gizmo')
                    self.gizmos.remove(gz)

                self._move_gz.clear()
                self._rotate_gz.clear()

        elif self.gz_motion_cam is None or update_gz:
            self.add_motion_cam_gz(context)

        # 矫正位置 move gizmo
        if self.gz_motion_cam:
            self.gz_motion_cam.matrix_basis = context.object.matrix_world.normalized()
            z = Vector((0, 0, 1))
            norm = z
            norm.rotate(context.object.matrix_world.to_euler('XYZ'))
            self.gz_motion_cam.matrix_basis.translation -= norm * context.object.motion_cam.offset_factor  # 修复偏移
            self.gz_motion_cam.matrix_basis.translation += z  # 向z移动

        # 矫正位置 rotate gizmo
        if self.gz_motion_cam:
            self.correct_rotate_gz_euler()

        context.area.tag_redraw()


def register():
    bpy.utils.register_class(CAMHP_UI_persp_view)
    bpy.utils.register_class(CAMHP_UI_cam_view)
    bpy.utils.register_class(CAMHP_OT_insert_keyframe)
    bpy.utils.register_class(CAMHP_OT_rotate_object)
    bpy.utils.register_class(CAMHP_GT_custom_move_1d)
    bpy.utils.register_class(CAMHP_GT_custom_move_3d)
    bpy.utils.register_class(CAMHP_GT_custom_rotate_1d)
    bpy.utils.register_class(CAMHP_UI_motion_curve_gz)


def unregister():
    bpy.utils.unregister_class(CAMHP_UI_persp_view)
    bpy.utils.unregister_class(CAMHP_UI_cam_view)
    bpy.utils.unregister_class(CAMHP_OT_insert_keyframe)
    bpy.utils.unregister_class(CAMHP_OT_rotate_object)
    bpy.utils.unregister_class(CAMHP_GT_custom_move_1d)
    bpy.utils.unregister_class(CAMHP_GT_custom_move_3d)
    bpy.utils.unregister_class(CAMHP_GT_custom_rotate_1d)
    bpy.utils.unregister_class(CAMHP_UI_motion_curve_gz)
