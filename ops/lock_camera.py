import bpy


class CAMHP_OT_lock_cam(bpy.types.Operator):
    """Camera to View"""
    bl_idname = 'camhp.lock_cam'
    bl_label = 'Lock View'

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D' and context.scene.camera:
            space = [i for i in context.area.spaces if i.type == "VIEW_3D"][0]
            return space and space.region_3d.view_perspective == 'CAMERA'
        return False

    def execute(self, context):
        setattr(context.space_data, "lock_camera", not getattr(context.space_data, "lock_camera"))
        return {'FINISHED'}
