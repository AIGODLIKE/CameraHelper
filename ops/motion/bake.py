
# bake motion camera
class CAMHP_OT_bake_motion_cam(bpy.types.Operator):
    bl_idname = "camhp.bake_motion_cam"
    bl_label = "Bake Motion Camera"

    frame_start: IntProperty(name="Start Frame", default=1)
    frame_end: IntProperty(name="End Frame", default=100)
    frame_step: IntProperty(name="Frame Step", default=1)

    # bake
    cam = None
    ob = None
    timer = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            ob = self.cam_bake
            affect = self.affect
            cam = self.cam

            if self.frame > self.frame_end:
                context.window_manager.event_timer_remove(self.timer)
                return {'FINISHED'}
            else:
                self.frame += self.frame_step

            context.scene.frame_set(self.frame)
            matrix = context.object.matrix_world.copy()
            print('frame', self.frame, matrix)
            # 位置
            loc = matrix.to_translation()
            ob.location = loc
            ob.keyframe_insert('location')

            if affect.use_euler:
                if self.euler_prev is None:
                    euler = matrix.to_euler(context.object.rotation_mode)
                else:
                    euler = matrix.to_euler(context.object.rotation_mode, self.euler_prev)
                self.euler_prev = euler.copy()

                ob.rotation_euler = self.euler_prev
                ob.keyframe_insert('rotation_euler')

            if not cam: return {'PASS_THROUGH'}
            # 相机数值
            if affect.use_lens:
                ob.data.lens = G_PROPS['lens']
                ob.data.keyframe_insert('lens')

            if affect.use_focus_distance:
                ob.data.dof.focus_distance = G_PROPS['focal']
                ob.data.dof.keyframe_insert('focus_distance')

            if affect.use_aperture_fstop:
                ob.data.dof.aperture_fstop = G_PROPS['fstop']
                ob.data.dof.keyframe_insert('aperture_fstop')

            # 自定义属性
            # for item in affect.custom_props:
            #     if item.data_path == '': continue
            #
            #     tg_obj = ob
            #     from_obj = context.object
            #
            #     src_obj, src_attr = parse_data_path(tg_obj.data, item.data_path)
            #     _from_obj, from_attr = parse_data_path(from_obj.data, item.data_path)
            #     if from_attr is None or src_attr is None or src_obj is None: continue
            #
            #     from_value = getattr(_from_obj, from_attr)
            #
            #     try:
            #         if isinstance(from_value, float):
            #             setattr(src_obj, src_attr, from_value)
            #         elif isinstance(from_value, mathutils.Vector):
            #             setattr(src_obj, src_attr, from_value)
            #         elif isinstance(from_value, mathutils.Matrix):
            #             setattr(src_obj, src_attr, from_value)
            #         elif isinstance(from_value, bool):
            #             setattr(src_obj, src_attr, from_value)
            #         elif isinstance(from_value, bpy.types.Object):
            #             setattr(src_obj, src_attr, from_value)
            #
            #         if hasattr(src_obj, 'keyframe_insert'):
            #             kf = getattr(src_obj, 'keyframe_insert')
            #             kf(src_attr)
            #
            #     except Exception as e:
            #         print(e)

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        # print('invoke')
        wm = context.window_manager
        m_cam = context.object.motion_cam
        affect = m_cam.affect

        if context.object.type == 'CAMERA':
            cam = context.object
        elif (affect.use_sub_camera and
              affect.sub_camera and
              affect.sub_camera.type == 'CAMERA'):

            cam = affect.sub_camera
        else:
            cam = None

        if cam is None:
            self.report({'ERROR'}, "无相机")
            return {'CANCELLED'}

        if m_cam.id_data.animation_data is None:
            self.report({'ERROR'}, "无动画")
            return {'CANCELLED'}

        action = m_cam.id_data.animation_data.action

        if action is None:
            self.report({'ERROR'}, "无动作")
            return {'CANCELLED'}

        self.frame_start = int(action.frame_range[0])
        self.frame_end = int(action.frame_range[1])

        name = cam.name + '_bake'
        data_name = cam.data.name + '_bake'
        # print(name, data_name)
        cam_data = bpy.data.cameras.new(name=data_name)
        ob = bpy.data.objects.new(name, cam_data)
        # ob.constraints.clear()
        # ob.location = 0, 0, 0

        context.collection.objects.link(ob)

        context.scene.frame_set(self.frame_start)

        self.frame = self.frame_start
        self.cam = cam
        self.cam_bake = ob
        self.affect = affect
        self.euler_prev = None
        # print('invoke end')
        self.timer = wm.event_timer_add(0.01, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}
        # return wm.invoke_props_dialog(self)

