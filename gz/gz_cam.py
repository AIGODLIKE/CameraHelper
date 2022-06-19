import bpy
from bpy.types import GizmoGroup, SpaceView3D


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


from .draw_utils.shader import CameraMotionPath
from .gz_custom import CAMHP_GT_custom_move_3d


class CAMHP_UI_draw_motion_curve(UI_Base, GizmoGroup):
    bl_idname = "CAMHP_UI_draw_motion_curve"
    bl_label = "Camera Motion Curve"
    bl_options = {'3D', 'PERSISTENT'}

    _instance = None
    _draw_handler_instance = None
    _thumbnail_instance = None

    _move_gz = dict()
    _rotate_gz = dict()
    _bind_set_get = dict()

    @classmethod
    def poll(cls, context):
        res = cls._poll(context)
        return res

    @classmethod
    def _poll(cls, context):
        ob = context.object
        view = context.space_data

        if ob and ob.type in {'CAMERA',
                              'EMPTY'} and view.region_3d.view_perspective != 'CAMERA' and not view.region_quadviews:
            if not cls._thumbnail_instance:
                cls._thumbnail_instance = CameraMotionPath(context)
                cls.start_draw_handler(context)
            return True
        else:
            cls.stop_draw_handler()
            return False

    @classmethod
    def stop_draw_handler(cls):
        if cls._draw_handler_instance:
            print("GZG::stop_draw_handler")
            try:
                SpaceView3D.draw_handler_remove(cls._draw_handler_instance, 'WINDOW')
            except ValueError:
                print(
                    "ERROR: DRAW HANDLER -> ValueError: callback_remove(handler): NULL handler given, invalid or already removed")
            cls._draw_handler_instance = None
            cls._thumbnail_instance = None
            return True
        return False

    @classmethod
    def start_draw_handler(cls, context):
        if cls._draw_handler_instance:
            # cls.stop_draw_handler()
            return
        print("GZG::start_draw_handler")
        cls._draw_handler_instance = SpaceView3D.draw_handler_add(
            cls._thumbnail_instance, (context,), 'WINDOW', 'POST_VIEW'
        )

    def draw_prepare(self, context):
        thumbnail = self.__class__._thumbnail_instance

        if not thumbnail:
            return

    def setup(self, context):
        self.__class__._instance = self

        self.add_motion_cam_gz(context)
        self.draw_prepare(context)

    def add_motion_cam_gz(self, context):

        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.target_set_prop('offset', context.object.motion_cam, 'offset_factor')
        gz.matrix_basis = context.object.matrix_world
        gz.draw_style = 'BOX'
        gz.use_tooltip = True
        gz.use_draw_modal = True
        gz.alpha = .6
        gz.color = 0.8, 0.0, 0.0
        gz.color_highlight = 1, 0.0, 0.0
        gz.alpha_highlight = 0.8
        self.gz_motion_cam = gz

        indexs = iter(range(len(context.object.motion_cam.list)))

        for index, item in enumerate(context.object.motion_cam.list):
            item = context.object.motion_cam.list[index]

            gz = self.gizmos.new("CAMHP_GT_custom_move_3d")
            gz._index = index

            gz.target_set_prop('offset', item.camera, 'location')
            # print(gz.target_get_value('offset'))
            # gz.matrix_basis = item.camera.matrix_world
            gz.use_tooltip = True
            gz.use_draw_modal = True
            gz.alpha = .6
            gz.color = 0.0, 0.6, 0.8
            gz.color_highlight = 0.0, 0.8, 1.0
            gz.alpha_highlight = 0.8
            gz.scale_basis = 0.2

            self._move_gz[gz] = item.camera

    def refresh(self, context):
        # print("GZG::refresh")

        if len(context.object.motion_cam.list) == 0:
            if self.gz_motion_cam:
                self.gizmos.remove(self.gz_motion_cam)
                self.gz_motion_cam = None

                for gz in self._move_gz.keys():
                    self.gizmos.remove(gz)
                self._move_gz.clear()
        else:
            if self.gz_motion_cam is None:
                self.add_motion_cam_gz(context)

            if self.gz_motion_cam.is_modal is False:
                self.gz_motion_cam.matrix_basis = context.object.matrix_world

            for gz, camera in self._rotate_gz.items():
                if gz.is_modal is False and camera:
                    gz.matrix_basis = camera.matrix_world.normalized()

        context.area.tag_redraw()


def register():
    bpy.utils.register_class(CAMHP_UI_persp_view)
    bpy.utils.register_class(CAMHP_UI_cam_view)
    bpy.utils.register_class(CAMHP_GT_custom_move_3d)
    bpy.utils.register_class(CAMHP_UI_draw_motion_curve)


def unregister():
    bpy.utils.unregister_class(CAMHP_UI_persp_view)
    bpy.utils.unregister_class(CAMHP_UI_cam_view)
    bpy.utils.unregister_class(CAMHP_GT_custom_move_3d)
    bpy.utils.unregister_class(CAMHP_UI_draw_motion_curve)
