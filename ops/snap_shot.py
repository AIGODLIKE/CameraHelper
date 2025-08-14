import bpy


class SnapShot(bpy.types.Operator):
    """Snap Shot"""
    bl_idname = "camhp.pv_snap_shot"
    bl_label = "Snap Shot"

    def execute(self, context):
        from .preview_camera import CameraThumbnails
        area = context.area
        if camera_data := CameraThumbnails.get_camera_data(area):
            if camera_name := camera_data.get("camera_name", None):
                if texture_data := CameraThumbnails.texture_data.get(camera_name, None):
                    if texture := texture_data.get('texture', None):
                        x = context.scene.render.resolution_x
                        y = context.scene.render.resolution_y
                        key  =f"Snap_Shot_{camera_name}"
                        if key in bpy.data.images:
                            img = bpy.data.images[key]
                            bpy.data.images.remoe(img)
                        img = bpy.data.images.new(name=key,
                                                  width=x,
                                                  height=y)
                        img.scale(x, y)

                        try:
                            img.pixels.foreach_set(texture.read())
                        except TypeError as e:
                            print(e)
                            return {'CANCELLED'}

                        bpy.ops.render.view_show('INVOKE_DEFAULT')
                        for area in context.screen.areas:
                            if area.type == 'IMAGE_EDITOR':
                                for space in area.spaces:
                                    if space.type == 'IMAGE_EDITOR':
                                        space.image = img
                                        break
                        self.report({'INFO'}, f'Snap Shot')
                # # set resolution
                # ori_width = context.scene.render.resolution_x
                # ori_height = context.scene.render.resolution_y
                # context.scene.render.resolution_x = self.width
                # context.scene.render.resolution_y = self.height
                #
                # bpy.ops.render.view_show('INVOKE_DEFAULT')
                # if context.window.screen.areas[0].type == 'IMAGE_EDITOR':
                #     # set img as area active image
                #     context.window.screen.areas[0].spaces[0].image = img
                #
                # # restore
                # context.scene.render.resolution_x = ori_width
                # context.scene.render.resolution_y = ori_height

        return {'FINISHED'}
