import bpy


class CAMHP_OT_switch_cam(bpy.types.Operator):
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
                # enum_items.insert(0, (obj.name, obj.name, '', 'VIEW_CAMERA', i))
                enum_items.append((obj.name, obj.name, '', 'VIEW_CAMERA', i))
            else:
                enum_items.append((obj.name, obj.name, '', 'DOT', i))

        return enum_items

    enum_cam: bpy.props.EnumProperty(
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
