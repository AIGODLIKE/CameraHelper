
class CAMHP_OT_move_view_between_cams(Operator):
    bl_idname = 'camhp.move_view_between_cams'
    bl_label = 'Move View Between Cameras'
    bl_options = {"INTERNAL"}

    r3d = None  # 当前region

    # camera
    tg_cam: StringProperty()  # pass in
    tg_loc = None
    tg_quat = None

    ori_view_distance = None
    ori_view_location = None
    ori_view_rotation = None
    ori_view_lens = None
    # 动画控制
    anim_fac = 0  # 动画比例 0~1
    anim_iter = 60  # 动画更新 秒
    anim_time = 0.5  # 持续时间 秒
    anim_out = 0.4  # 退出动画比例

    _timer = None

    @classmethod
    def poll(self, context):
        return context.area.type == 'VIEW_3D'

    def remove_handle(self):
        # bpy.types.SpaceNodeEditor.draw_handler_remove(self._handle, 'WINDOW')
        bpy.context.window_manager.event_timer_remove(self._timer)

    def append_handle(self):
        self._timer = bpy.context.window_manager.event_timer_add(self.anim_time / self.anim_iter,
                                                                 window=bpy.context.window)  # 添加计时器检测状态
        args = (self, bpy.context)
        # self._handle = bpy.types.SpaceNodeEditor.draw_handler_add(draw_process_callback_px, args, 'WINDOW',
        #                                                           'POST_PIXEL')
        bpy.context.window_manager.modal_handler_add(self)

    def offset_view(self, anim_fac):
        fac = anim_fac
        cam = bpy.context.scene.camera.data

        offset_loc = self.ori_view_location.lerp(self.tg_loc, fac)
        offset_rot = self.ori_view_rotation.slerp(self.tg_quat, fac)
        offset_alpha = self.ori_passepartout_alpha * fac

        self.r3d.view_location = offset_loc
        self.r3d.view_rotation = offset_rot

        bpy.context.space_data.lens = self.ori_view_lens[0] + (
                cam.lens - self.ori_view_lens[0]) * fac / self.anim_out  # 加快
        cam.passepartout_alpha = offset_alpha

    def correct_offset(self):
        """ 用于最终位置矫正

        :return:
        """
        # correct
        self.r3d.view_location = self.tg_loc
        self.r3d.view_rotation = self.tg_quat
        self.r3d.view_camera_zoom = 0
        self.r3d.view_perspective = 'CAMERA'
        bpy.context.space_data.lens = bpy.context.scene.camera.data.lens
        # bpy.ops.view3d.view_camera("INVOKE_DEFAULT")

    def restore(self):
        """ 复位，恢复用户的选择距离和视口位置

        :return:
        """
        self.r3d.view_distance = 6
        # self.r3d.view_distance = self.ori_view_distance[0]
        # self.r3d.view_location = self.ori_view_location
        # self.r3d.view_rotation = self.ori_view_rotation
        bpy.context.space_data.lens = self.ori_view_lens[0]
        bpy.context.scene.camera.data.passepartout_alpha = self.ori_passepartout_alpha

    def invoke(self, context, event):
        area = context.area
        self.r3d = area.spaces[0].region_3d
        tg = bpy.data.objects[self.tg_cam]

        self.tg_loc = tg.matrix_world.to_translation().copy()
        self.tg_quat = tg.matrix_world.to_quaternion().copy()

        self.ori_passepartout_alpha = tg.data.passepartout_alpha
        self.ori_view_distance = (self.r3d.view_distance,)  # 放入元组防止变化
        self.ori_view_location = self.r3d.view_location
        self.ori_view_rotation = self.r3d.view_rotation
        self.ori_view_lens = (getattr(context.space_data, "lens"),)  # 放入元组防止变化

        self.append_handle()
        # 进入一般界面, 设置相机
        self.r3d.view_distance = 0
        self.r3d.view_perspective = 'PERSP'
        context.scene.camera = bpy.data.objects[self.tg_cam]

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        context.region.tag_redraw()

        if event.type == 'TIMER':
            if self.anim_fac >= self.anim_out:  # 加快进入
                self.remove_handle()
                # 强制对齐
                self.correct_offset()
                self.restore()
                return {'FINISHED'}
            # 移动动画
            self.offset_view(self.anim_fac)
            self.anim_fac += 1 / (self.anim_iter + 1)  # last delay

        return {"PASS_THROUGH"}

