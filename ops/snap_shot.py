


@persistent
def load_file_clear_handle(noob):
    print('Camera Helper Clear Handle')
    CameraThumbHandle.clear_handle()
    bpy.context.window_manager.camhp_pv.enable = False


class CAMHP_OT_pv_snap_shot(bpy.types.Operator):
    """Snap Shot"""
    bl_idname = "camhp.pv_snap_shot"
    bl_label = "Snap Shot"

    @classmethod
    def poll(cls, context):
        return CameraThumbHandle.inst

    def invoke(self, context, event):
        context.window_manager.camhp_snap_shot_image = True
        return self.execute(context)

    def execute(self, context):
        self.width = CameraThumbHandle.inst.width
        self.height = CameraThumbHandle.inst.height

        cam = CameraThumbHandle.inst.cam
        buffer = CameraThumbHandle.inst.buffer

        if f'_SnapShot_{cam.name}' in bpy.data.images:
            img = bpy.data.images[f'_SnapShot_{cam.name}']
        else:
            img = bpy.data.images.new(name=f'_SnapShot_{cam.name}',
                                      width=self.width,
                                      height=self.height)

        img.scale(self.width, self.height)
        try:
            img.pixels.foreach_set(buffer)
        except TypeError as e:
            print(e)
            return {'CANCELLED'}
        # set resolution
        ori_width = context.scene.render.resolution_x
        ori_height = context.scene.render.resolution_y
        context.scene.render.resolution_x = self.width
        context.scene.render.resolution_y = self.height

        bpy.ops.render.view_show('INVOKE_DEFAULT')
        if context.window.screen.areas[0].type == 'IMAGE_EDITOR':
            # set img as area active image
            context.window.screen.areas[0].spaces[0].image = img

        # restore
        context.scene.render.resolution_x = ori_width
        context.scene.render.resolution_y = ori_height

        context.window_manager.camhp_snap_shot_image = False
        self.report({'INFO'}, f'Snap Shot')

        return {'FINISHED'}