import bpy
import importlib
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
        ui_scale = context.preferences.view.ui_scale
        region = context.region

        step = 40
        icon_scale = (80 * 0.35) / 2  # 14
        # 从屏幕右侧起
        start_x = region.width - (icon_scale + step) / 2 * ui_scale
        start_y = region.height

        # 检查是否启用区域重叠，若启用则加上宽度以符合侧面板移动
        if context.preferences.system.use_region_overlap:
            for region in context.area.regions:
                if region.type == 'UI':
                    start_x -= region.width
                    break
        # 检查是否开启坐标轴
        if context.preferences.view.mini_axis_type == 'MINIMAL':
            size = context.preferences.view.mini_axis_size
            start_y -= size * ui_scale + step * 2 * ui_scale
        elif context.preferences.view.mini_axis_type == 'GIZMO':
            size = context.preferences.view.gizmo_size_navigate_v3d
            start_y -= size * ui_scale + step * 2 * ui_scale
        elif context.preferences.view.mini_axis_type == 'NONE':
            start_y -= step * 2 * ui_scale

        # 检查是否开启默认控件
        if context.preferences.view.show_navigate_ui:
            start_y -= (icon_scale + step) * 3 * ui_scale
        else:
            start_y -= step * 2 * ui_scale

        for i, gz in enumerate(self.gizmos):
            gz.matrix_basis[0][3] = start_x
            gz.matrix_basis[1][3] = start_y - step * i * ui_scale
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
        if context.scene.camhp_pv.enable:
            self.gz_cam_pv.color = 0.08, 0.6, 0.08
            self.gz_cam_pv.color_highlight = 0.28, 0.8, 0.28

            if context.scene.camhp_pv.pin:
                self.gz_cam_pv.color = 0.8, 0.2, 0.2
                self.gz_cam_pv.color_highlight = 1, 0.2, 0.2
        else:
            self.gz_cam_pv.color = 0.08, 0.08, 0.08
            self.gz_cam_pv.color_highlight = 0.28, 0.28, 0.28


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


from .gz_custom import CAMHP_GT_custom_move_3d, CAMHP_GT_custom_move_1d, CAMHP_OT_insert_keyframe
from ..prefs.get_pref import get_pref


class CAMHP_UI_motion_curve_gz(GizmoGroupBase, GizmoGroup):
    bl_idname = "CAMHP_UI_motion_curve_gz"
    bl_label = "Camera Motion Curve"
    bl_options = {'3D', 'PERSISTENT'}

    _move_gz = dict()
    cam_list = list()

    @classmethod
    def poll(cls, context):
        ob = context.object
        view = context.space_data
        if all((
                ob,
                ob.type in {'CAMERA', 'EMPTY'},
                view.region_3d.view_perspective != 'CAMERA',
                not view.region_quadviews
        )):
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

        for gz in self._move_gz.keys():
            self.gizmos.remove(gz)

        self._move_gz.clear()

        for index, item in enumerate(context.object.motion_cam.list):
            item = context.object.motion_cam.list[index]

            gz = self.gizmos.new("CAMHP_GT_custom_move_3d")
            gz._index = index
            gz._camera = item.camera

            gz.target_set_prop('offset', item.camera, 'location')
            # gz.target_set_handler(
            #     "offset",
            #     get=props.get_value,
            #     set=props.set_value,
            # )
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

                self._move_gz.clear()

        elif self.gz_motion_cam is None or update_gz:
            self.add_motion_cam_gz(context)

        # 矫正位置
        if self.gz_motion_cam:
            self.gz_motion_cam.matrix_basis = context.object.matrix_world.normalized()
            self.gz_motion_cam.matrix_basis.col[3][2] += 0.5

        context.area.tag_redraw()


def register():
    bpy.utils.register_class(CAMHP_UI_persp_view)
    bpy.utils.register_class(CAMHP_UI_cam_view)
    bpy.utils.register_class(CAMHP_OT_insert_keyframe)
    bpy.utils.register_class(CAMHP_GT_custom_move_1d)
    bpy.utils.register_class(CAMHP_GT_custom_move_3d)
    bpy.utils.register_class(CAMHP_UI_motion_curve_gz)


def unregister():
    bpy.utils.unregister_class(CAMHP_UI_persp_view)
    bpy.utils.unregister_class(CAMHP_UI_cam_view)
    bpy.utils.unregister_class(CAMHP_OT_insert_keyframe)
    bpy.utils.unregister_class(CAMHP_GT_custom_move_1d)
    bpy.utils.unregister_class(CAMHP_GT_custom_move_3d)
    bpy.utils.unregister_class(CAMHP_UI_motion_curve_gz)
