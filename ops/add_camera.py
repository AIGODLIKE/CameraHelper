import bpy


class CAMHP_OT_add_view_cam(bpy.types.Operator):
    """Add View Camera\nCtrl Left Click: Add Motion Camera"""
    bl_idname = 'camhp.add_view_cam'
    bl_label = 'Add View Camera'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D'

    def execute(self, context):
        # 创建相机
        cam_data = bpy.data.cameras.new(name='Camera')
        cam = bpy.data.objects.new('Camera', cam_data)
        context.collection.objects.link(cam)
        # 设置
        cam.data.show_name = True
        # 进入视图
        context.scene.camera = cam
        context.view_layer.objects.active = cam
        try:
            bpy.ops.view3d.camera_to_view()
        except:
            pass

        area = context.area
        space = [i for i in area.spaces if i.type == "VIEW_3D"][0]
        r3d = space.region_3d
        r3d.view_camera_zoom = 0

        context.region.tag_redraw()

        return {"FINISHED"}

    def invoke(self, context, event):
        if event.ctrl:
            bpy.ops.camhp.add_motion_cams('INVOKE_DEFAULT')
            bpy.ops.ed.undo_push()
            return {'FINISHED'}
        else:
            return self.execute(context)
