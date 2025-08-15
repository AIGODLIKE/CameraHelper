import blf
import bpy
import gpu.matrix
from gpu_extras.presets import draw_texture_2d
from mathutils import Vector

from .public_gizmo import PublicGizmo
from ..debug import DEBUG_PREVIEW_CAMERA
from ..camera_thumbnails import CameraThumbnails
from ..utils.area import area_offset
from ..utils.gpu import draw_box


class PreviewCameraAreaGizmo(bpy.types.Gizmo):
    bl_idname = "PREVIEW_CAMERA_GT_gizmo"
    bl_options = {"PERSISTENT", "SCALE", "SHOW_MODAL_ALL", "UNDO", "GRAB_CURSOR"}

    draw_points = None
    is_hover = None
    start_offset = None
    start_mouse = None
    offset_after = None

    def invoke(self, context, event):
        self.start_offset = CameraThumbnails.get_camera_data(context.area)["offset"]
        self.start_mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        if DEBUG_PREVIEW_CAMERA:
            print("invoke")
        return {"RUNNING_MODAL"}

    def modal(self, context, event, tweak):
        if DEBUG_PREVIEW_CAMERA:
            print(self.bl_idname, "modal", event.type, event.value, CameraThumbnails.get_camera_data(context.area))
        if event.type == "LEFTMOUSE":
            return {"FINISHED"}
        elif event.type in {"RIGHTMOUSE", "ESC"}:
            return {"CANCELLED"}
        mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        diff = self.start_mouse - mouse
        self.offset_after = offset = self.start_offset + Vector((-diff.x, diff.y))
        CameraThumbnails.get_camera_data(context.area)["offset"] = offset
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def exit(self, context, cancel):
        if DEBUG_PREVIEW_CAMERA:
            print("exit", cancel)
        if cancel:
            CameraThumbnails.get_camera_data(context.area)["offset"] = self.start_offset
        else:
            CameraThumbnails.get_camera_data(context.area)["offset"] = self.offset_after

    def draw(self, context):
        """
        从左上角开始绘制
        """
        from ..utils import get_camera_preview_size
        w, h = get_camera_preview_size(context)
        with gpu.matrix.push_pop():
            gpu.state.depth_mask_set(False)
            data = CameraThumbnails.get_camera_data(context.area)
            offset = data["offset"]
            x, y = area_offset(context) + offset
            y = context.area.height - y
            y -= h
            gpu.matrix.translate((x, y))

            color = (.1, .1, .1, 0) if self.is_hover else (.2, .2, .2, .5)
            border = 5
            draw_box(-border, w + border, -border, h + border, color)

            if texture := CameraThumbnails.texture_data.get(data["camera_name"], None):
                draw_texture_2d(texture, (0, 0), w, h)
            # DEBUG
            if DEBUG_PREVIEW_CAMERA:
                blf.position(0, 0, 0, 1)
                for text in (
                        f"Preview Camera {self.is_hover}",
                        hash(context.area),
                        texture,
                        f"{self.draw_points}",
                        str(data)
                ):
                    gpu.matrix.translate((0, -15))
                    blf.draw(0, str(text))
            self.draw_points = (x, y), (x + w, y + h)

    def test_select(self, context, mouse_pos):
        if self.draw_points is None:
            return -1
        x, y = mouse_pos
        (x1, y1), (x2, y2) = self.draw_points
        x_ok = x1 < x < x2
        y_ok = y1 < y < y2
        is_hover = 0 if x_ok and y_ok else -1
        self.is_hover = is_hover == 0
        return is_hover

    def refresh(self, context):
        if DEBUG_PREVIEW_CAMERA:
            print(self.bl_idname, "refresh")


class PreviewCameraGizmos(bpy.types.GizmoGroup, PublicGizmo):
    bl_idname = "Preview_Camera_UI_gizmos"
    bl_label = "Preview Camera Gizmos"

    @classmethod
    def poll(cls, context):
        return CameraThumbnails.check_is_draw(context)

    def setup(self, context):
        gz = self.preview_camera = self.gizmos.new(PreviewCameraAreaGizmo.bl_idname)
        gz.use_draw_modal = True

    def refresh(self, context):
        context.area.tag_redraw()

    def draw_prepare(self, context):
        ...
