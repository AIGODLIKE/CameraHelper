

class pop_cam_panel(bpy.types.Panel):
    """Properties"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'


class CAMHP_PT_pop_cam_pv_panel(pop_cam_panel):
    bl_label = "Preview"
    bl_idname = 'CAMHP_PT_pop_cam_pv_panel'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.active = context.window_manager.camhp_pv.enable
        layout.prop(context.window_manager.camhp_pv, 'enable')
        layout.prop(context.window_manager.camhp_pv, 'pin')
        layout.operator('camhp.pv_snap_shot')
        # layout.prop(context.window_manager.camhp_pv, 'show_overlay')

