import time
from contextlib import contextmanager

import bpy
import gpu
from mathutils import Vector

from .debug import DEBUG_PREVIEW_CAMERA
from .utils import get_camera
from .utils.area import get_area_max_parent


@contextmanager
def camera_context(context):
    """Tips: 打开了渲染窗口会出现screen不匹配无法刷新"""
    for area in context.screen.areas:
        if area.type == "VIEW_3D":
            for region in area.regions:
                if region.type == "WINDOW":
                    for space in area.spaces:
                        if space.type == "VIEW_3D":
                            with context.temp_override(
                                    area=area,
                                    region=region,
                                    space_data=space,
                            ):
                                ori_show_overlay = space.overlay.show_overlays
                                space.overlay.show_overlays = False
                                yield True
                                space.overlay.show_overlays = ori_show_overlay
                                return
    yield False


class CameraThumbnails:
    """Camera Thumbnails\nLeft Click: Enable\nCtrl: Pin Selected Camera\nCtrl Shift Click: Send to Viewer"""

    camera_data = {
        # area:{
        # camera_name:str,
        # offset:Vector
        # pin:bool,
        # enabled:bool,
        # }
    }

    texture_data = {
        # camera_name:gpu.types.GPUTexture
    }

    @classmethod
    def pin_selected_camera(cls, context, camera: bpy.types.Camera):
        data = cls.camera_data
        area_hash = hash(get_area_max_parent(context.area))
        if area_hash not in data:
            cls.switch_preview(context, camera)

        data[area_hash]["enabled"] = True
        data[area_hash]["pin"] = data[area_hash]["pin"] ^ True

    @classmethod
    def switch_preview(cls, context, camera: bpy.types.Camera):
        data = cls.camera_data
        area_hash = hash(get_area_max_parent(context.area))
        if area_hash in data:
            data[area_hash]["enabled"] = data[area_hash]["enabled"] ^ True
        else:
            data[area_hash] = {
                "camera_name": camera.name,
                "offset": Vector((0, 0)),
                "pin": False,
                "enabled": True,
            }

    @classmethod
    def update(cls):
        from .debug import DEBUG_PREVIEW_CAMERA
        start_time = time.time()
        context = bpy.context
        camera = get_camera(context)

        if camera is not None:
            for key, value in cls.camera_data.items():  # 切换预览相机
                pin = value.get("pin", False)

                if DEBUG_PREVIEW_CAMERA:
                    print("pin\t", pin, "\t", value["camera_name"], key, value, )
                if pin is False:
                    value["camera_name"] = camera.name
                    cls.camera_data[key] = value

        update_completion_list = []
        with camera_context(context) as is_update:
            if is_update:
                if DEBUG_PREVIEW_CAMERA:
                    print(is_update, "cls.camera_data")
                for camera_data in cls.camera_data.values():  # 更新相机纹理
                    camera_name = camera_data["camera_name"]
                    camera = context.scene.objects.get(camera_name, None)
                    enabled = camera_data.get("enabled", False)
                    if camera and enabled and camera_name not in update_completion_list:
                        cls.update_camera_texture(context, camera)
                        update_completion_list.append(camera_name)

        if DEBUG_PREVIEW_CAMERA:
            print(f"update {time.time() - start_time}s\t", update_completion_list)
            print("\n")

    @classmethod
    def update_camera_texture(cls, context, camera, use_resolution=False) -> gpu.types.GPUTexture:
        from .utils import get_camera_preview_size

        is_update = True
        scene = context.scene
        name = camera.name

        if use_resolution:
            render = context.scene.render
            w, h = render.resolution_x, render.resolution_y
        else:
            w, h = get_camera_preview_size(context)

        texture = None
        if is_update:
            if name not in cls.camera_data:
                offscreen = gpu.types.GPUOffScreen(w, h)
            else:
                offscreen = cls.camera_data[name]
            view_matrix = camera.matrix_world.inverted()
            projection_matrix = camera.calc_matrix_camera(
                context.evaluated_depsgraph_get(),
                x=w,
                y=h,
            )
            offscreen.draw_view3d(
                scene,
                context.view_layer,
                context.space_data,
                context.region,
                view_matrix,
                projection_matrix,
                do_color_management=False,
                draw_background=True,
            )
            if DEBUG_PREVIEW_CAMERA:
                print("update_camera_texture", camera.name)
            texture = cls.texture_data[name] = offscreen.texture_color
        return texture

    @classmethod
    def check_is_draw(cls, context):
        area_hash = hash(get_area_max_parent(context.area))
        if area_hash in cls.camera_data:
            return cls.camera_data[area_hash]["enabled"]
        return False

    @classmethod
    def check_is_pin(cls, context):
        area_hash = hash(context.area)
        return area_hash in cls.camera_data and cls.camera_data[area_hash].get("pin", False)

    @classmethod
    def update_2d_button_color(cls, context, gizmo):
        if cls.check_is_draw(context):
            gizmo.color = 0.08, 0.6, 0.08
            gizmo.color_highlight = 0.28, 0.8, 0.28
            if cls.check_is_pin(context):
                gizmo.color = 0.8, 0.2, 0.2
                gizmo.color_highlight = 1, 0.2, 0.2
        else:
            gizmo.color = 0.08, 0.08, 0.08
            gizmo.color_highlight = 0.28, 0.28, 0.28

    @classmethod
    def get_camera_data(cls, area):
        area_hash = hash(get_area_max_parent(area))
        return CameraThumbnails.camera_data.get(area_hash, None)
