import bpy

from ..utils import offset_2d_gizmo


class PreviewCamera:
    ...


class Gizmos:
    def create_gizmo(self, name) -> bpy.types.Gizmo:
        gz = self.gizmos.new(name)
        gz.icon = 'VIEW_PERSPECTIVE'
        gz.draw_options = {'BACKDROP', 'OUTLINE'}
        gz.use_tooltip = True
        gz.use_draw_modal = True
        gz.alpha = .8
        gz.color = 0.08, 0.08, 0.08
        gz.color_highlight = 0.28, 0.28, 0.28
        gz.alpha_highlight = 0.8

        gz.scale_basis = (80 * 0.35) / 2  # Same as buttons defined in C
        return gz

    def create_adjust_camera(self, context):
        # 调整焦距控件
        from ..ops.adjust_camera_lens import AdjustCameraLens
        gz = self.create_gizmo("GIZMO_GT_button_2d")
        gz.icon = 'VIEW_PERSPECTIVE'
        gz.target_set_operator(AdjustCameraLens.bl_idname)
        self.gz_move = gz

    def create_camera_settings(self, context):
        # 相机设置
        gz = self.create_gizmo("GIZMO_GT_button_2d")
        gz.icon = 'PROPERTIES'
        props = gz.target_set_operator("wm.call_menu")
        props.name = "CAMHP_MT_popup_cam_settings"
        self.gz_setttings = gz

    def create_add_camera(self, context):
        from ..ops.add_camera import AddCamera
        gz = self.create_gizmo("GIZMO_GT_button_2d")
        gz.icon = 'ADD'
        gz.target_set_operator(AddCamera.bl_idname)
        self.gz_add_cam = gz

    def create_camera_preview(self, context):
        from ..ops.preview_camera import PreviewCamera
        gz = self.create_gizmo("GIZMO_GT_button_2d")
        gz.use_event_handle_all = True
        gz.icon = 'IMAGE_PLANE'
        gz.target_set_operator(PreviewCamera.bl_idname)
        self.gz_cam_pv = gz


class Button2DGizmos(bpy.types.GizmoGroup, Gizmos):
    bl_idname = "Button_UI_2D_gizmos"
    VIEW = 'CAMERA'

    bl_label = "View Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', 'SCALE', 'SHOW_MODAL_ALL'}

    def setup(self, context):
        self.create_add_camera(context)
        self.create_camera_preview(context)
        self.create_camera_settings(context)
        self.create_adjust_camera(context)

    def draw_prepare(self, context):
        for i, gz in enumerate(self.gizmos):
            offset_2d_gizmo(context, gz, i)
        context.area.tag_redraw()
        self.refresh(context)

    def refresh(self, context):
        context.area.tag_redraw()
        # if self.camera_preview_enabled:
        #     self.gz_cam_pv.color = 0.08, 0.6, 0.08
        #     self.gz_cam_pv.color_highlight = 0.28, 0.8, 0.28
        #
        #     if self.camera_preview_pin:
        #         self.gz_cam_pv.color = 0.8, 0.2, 0.2
        #         self.gz_cam_pv.color_highlight = 1, 0.2, 0.2
        # else:
        #     self.gz_cam_pv.color = 0.08, 0.08, 0.08
        #     self.gz_cam_pv.color_highlight = 0.28, 0.28, 0.28