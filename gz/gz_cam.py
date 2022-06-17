import bpy
from bpy.types import GizmoGroup


class UI_Base:
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

        # self.gz_lock.icon

        context.area.tag_redraw()


class CAMHP_UI_persp_view(UI_Base, GizmoGroup):
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

    #     self.add_gz_motion_cam(context)
    #
    # def refresh(self, context):
    #     self.set_gz_motion_cam(context)
    #     context.area.tag_redraw()
    #
    # def set_gz_motion_cam(self, context):
    #     """用于更新gz_lock的图标
    #
    #     :param context:
    #     :return:
    #     """
    #     try:
    #         self.gizmos.remove(self.gz_motion_cam)
    #     except:
    #         pass
    #     finally:
    #         if context.object.type in {'CAMERA', 'EMPTY'}:
    #             self.add_gz_motion_cam(context)
    #
    # def add_gz_motion_cam(self, context):
    #     if context.object.type not in {'CAMERA', 'EMPTY'}: return
    #     gz = self.gizmos.new("GIZMO_GT_button_2d")
    #     gz.icon = 'ARROW_LEFTRIGHT'
    #     gz.draw_options = {'BACKDROP', 'OUTLINE'}
    #     gz.use_tooltip = True
    #     gz.alpha = .8
    #     gz.color = 0.08, 0.08, 0.08
    #     gz.color_highlight = 0.28, 0.28, 0.28
    #     gz.alpha_highlight = 0.8
    #
    #     gz.scale_basis = (80 * 0.35) / 2  # Same as buttons defined in C
    #
    #     gz.select = True
    #     props = gz.target_set_operator("wm.call_panel", )
    #     props.curve_name = 'CAMHP_PT_MotionCamPanel'
    #     props.keep_open = False
    #     self.gz_motion_cam = gz


class CAMHP_UI_cam_view(UI_Base, GizmoGroup):
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

        self.add_gz_lock(context)


def register():
    bpy.utils.register_class(CAMHP_UI_persp_view)
    bpy.utils.register_class(CAMHP_UI_cam_view)


def unregister():
    bpy.utils.unregister_class(CAMHP_UI_persp_view)
    bpy.utils.unregister_class(CAMHP_UI_cam_view)
