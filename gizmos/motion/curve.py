

class CAMHP_UI_motion_curve_gz(GizmoGroupBase, GizmoGroup):
    bl_idname = "CAMHP_UI_motion_curve_gz"
    bl_label = "Camera Motion Curve"
    bl_options = {'3D', 'PERSISTENT'}

    _move_gz = dict()
    _rotate_gz = dict()
    _gz_axis = dict()

    cam_list = list()

    @classmethod
    def poll(cls, context):
        ob = context.object
        view = context.space_data
        if (
                ob and
                ob.type in {'CAMERA', 'EMPTY'} and
                view.region_3d.view_perspective != 'CAMERA' and
                not view.region_quadviews
        ):
            return True
        else:
            return False

    def draw_prepare(self, context):
        super().draw_prepare(context)
        self.refresh(context)

    def setup(self, context):
        self._move_gz = dict()
        self._rotate_gz = dict()
        self.gz_motion_cam = None

        self.cam_list = [item.camera for item in context.object.motion_cam.list]

        self.add_motion_cam_gz(context)
        self.draw_prepare(context)
        print(self._move_gz)

    def add_motion_cam_gz(self, context):
        if self.gz_motion_cam is None:
            gz = self.gizmos.new("CAMHP_GT_custom_move_1d")
            gz.target_set_prop('offset', context.object.motion_cam, 'offset_factor')

            gz._camera = context.object
            gz.use_tooltip = True
            gz.use_event_handle_all = True

            # 设置gizmo的偏好
            pref_gz = get_pref().gz_motion_camera

            gz.alpha = pref_gz.color[3]
            gz.color = pref_gz.color[:3]
            gz.color_highlight = pref_gz.color_highlight[:3]
            gz.alpha_highlight = pref_gz.color_highlight[3]

            gz.use_draw_modal = True
            gz.use_draw_scale = False

            self.gz_motion_cam = gz
        try:
            for gz in self._move_gz.keys():
                self.gizmos.remove(gz)

            for gz in self._rotate_gz.keys():
                self.gizmos.remove(gz)
        except ReferenceError:  # new file open
            pass

        self._move_gz = dict()
        self._rotate_gz = dict()
        self._gz_axis = dict()

        for index, item in enumerate(context.object.motion_cam.list):
            item = context.object.motion_cam.list[index]

            self.add_move_gz(index, item)
            print('Add gizmos')
            # TODO 移除gizmo以避免崩溃。 Blender报错：EXCEPTION_ACCESS_VIOLATION，联系官方处理中
            # TODO 已经解决，似乎是python的锅 https://projects.blender.org/blender/blender/issues/109111#issuecomment-963329
            self.add_rotate_gz(item, 'X')
            self.add_rotate_gz(item, 'Y')
            self.add_rotate_gz(item, 'Z')

        self.correct_rotate_gz_euler()

    def correct_rotate_gz_euler(self):
        for gz, axis in self._gz_axis.items():
            if axis == 'X':
                rotate = Euler((math.radians(90), math.radians(-180), math.radians(-90)), 'XYZ')  # 奇怪的数值

            elif axis == 'Y':
                rotate = Euler((math.radians(-90), 0, 0), 'XYZ')

            else:
                rotate = Euler((0, 0, math.radians(90)), 'XYZ')

            cam = self._rotate_gz[gz]
            # print('correct gizmos')
            rotate.rotate(cam.matrix_world.to_euler('XYZ'))
            gz.matrix_basis = rotate.to_matrix().to_4x4()
            gz.matrix_basis.translation = cam.matrix_world.translation

    def add_rotate_gz(self, item, axis='Z'):
        # rotate gizmos
        # gizmos = self.gizmos.new("GIZMO_GT_dial_3d")
        gz = self.gizmos.new("CAMHP_GT_custom_rotate_1d")

        prop = gz.target_set_operator(CAMHP_OT_rotate_object.bl_idname)
        prop.obj_name = item.camera.name
        prop.axis = axis

        gz.use_tooltip = True
        gz.use_event_handle_all = True

        gz.use_draw_modal = True
        gz.use_draw_scale = False

        # red, green, blue for X Y Z axis
        gz.alpha = 0.5
        gz.alpha_highlight = 1

        ui = bpy.context.preferences.themes[0].user_interface

        axis_x = ui.axis_x[:3]
        axis_y = ui.axis_y[:3]
        axis_z = ui.axis_z[:3]

        if axis == 'X':
            gz.color = axis_x
        elif axis == 'Y':
            gz.color = axis_y
        elif axis == 'Z':
            gz.color = axis_z

        gz.color_highlight = (1, 1, 1)

        self._rotate_gz[gz] = item.camera
        self._gz_axis[gz] = axis

    def add_move_gz(self, index, item):
        # move gizmos
        gz = self.gizmos.new("CAMHP_GT_custom_move_3d")
        gz._index = index
        gz._camera = item.camera

        gz.target_set_prop('offset', item.camera, 'location')

        gz.use_tooltip = True
        gz.use_event_handle_all = True

        pref_gz = get_pref().gz_motion_source
        gz.alpha = pref_gz.color[3]
        gz.color = pref_gz.color[:3]
        gz.color_highlight = pref_gz.color_highlight[:3]
        gz.alpha_highlight = pref_gz.color_highlight[3]

        gz.use_draw_modal = True
        gz.use_draw_scale = False

        self._move_gz[gz] = item.camera

    def refresh(self, context):
        # print("CamHp::refresh")
        update_gz = False
        # 添加相机时候自动添加gizmo
        cam_list = [item.camera for item in context.object.motion_cam.list]
        if self.cam_list != cam_list:
            self.cam_list = cam_list
            update_gz = True

        # 切换物体移除gizmo
        if len(context.object.motion_cam.list) == 0:
            if self.gz_motion_cam:
                self.gizmos.remove(self.gz_motion_cam)
                self.gz_motion_cam = None

                for gz in self._move_gz.keys():
                    self.gizmos.remove(gz)

                for gz in self._rotate_gz.keys():
                    # print('remove gizmos')
                    self.gizmos.remove(gz)

                self._move_gz = dict()
                self._rotate_gz = dict()

        elif self.gz_motion_cam is None or update_gz:
            self.add_motion_cam_gz(context)

        # 矫正位置 move gizmos
        if self.gz_motion_cam:
            self.gz_motion_cam.matrix_basis = context.object.matrix_world.normalized()
            z = Vector((0, 0, 1))
            norm = z
            norm.rotate(context.object.matrix_world.to_euler('XYZ'))
            self.gz_motion_cam.matrix_basis.translation -= norm * context.object.motion_cam.offset_factor  # 修复偏移
            self.gz_motion_cam.matrix_basis.translation += z  # 向z移动

        # 矫正位置 rotate gizmos
        if self.gz_motion_cam:
            self.correct_rotate_gz_euler()

        context.area.tag_redraw()

