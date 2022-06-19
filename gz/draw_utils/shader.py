import bpy
import bgl
import gpu
import math
import mathutils
import ast
import numpy as np

from bpy_extras.view3d_utils import location_3d_to_region_2d
from gpu_extras.batch import batch_for_shader
from .bl_ui_slider import BL_UI_Slider
from .bl_ui_drag_panel import BL_UI_Drag_Panel

shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')


class CameraMotionPath():

    def __init__(self, context):
        self.context = context

    def __call__(self, context):
        self.draw(context)

    def draw(self, context):
        self.draw_callback_bezier_3d(context)

    def draw_callback_bezier_3d(self, context):
        self.motion_path = context.object.motion_cam.path
        if self.motion_path is None: return
        if context.object.motion_cam.path_points == '': return

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glEnable(bgl.GL_DEPTH_TEST)

        points = context.object.motion_cam.path_points.split('$')
        pts = [ast.literal_eval(p) for p in points]

        bgl.glLineWidth(3)
        shader.bind()
        shader.uniform_float("color", (0.8, 0, 0, 0.5))
        batch = batch_for_shader(shader, 'LINES', {"pos": pts})
        batch.draw(shader)

        # restore opengl defaults
        bgl.glLineWidth(1)
        bgl.glDisable(bgl.GL_BLEND)
        bgl.glDisable(bgl.GL_LINE_SMOOTH)
        bgl.glEnable(bgl.GL_DEPTH_TEST)


class CameraSlider():
    def __init__(self, context):
        self.context = context
        self.widgets = list()

        widgets_panel = list()

        self.panel = BL_UI_Drag_Panel(100, 500, 300, 290)
        self.panel.bg_color = (0.2, 0.2, 0.2, 0.9)
        self.widgets.append(self.panel)

        self.slider = BL_UI_Slider(20, 50, 260, 30)
        self.slider.color = (0.2, 0.8, 0.8, 0.8)
        self.slider.hover_color = (0.2, 0.9, 0.9, 1.0)
        self.slider.min = 0.0
        self.slider.max = 1.0
        # self.slider.set_value(0.0)
        self.slider.decimals = 2
        self.slider.show_min_max = True
        self.slider.set_value_change(self.on_slider_value_change)

        self.panel.add_widgets(widgets_panel)
        self.widgets.append(self.slider)

        for w in self.widgets:
            w.init(context)

    def __call__(self, context):
        self.draw(context)

    def draw(self, context):
        self.draw_widget(context)

    def on_slider_value_change(self, value):
        obj = self.context.object
        obj.motion_cam.offset_factor = (1, 1, value)

    def draw_widget(self, context):

        for widget in self.widgets:
            widget.draw()

    def handle_widget_events(self, event):
        result = False
        for widget in self.widgets:
            if widget.handle_event(event):
                result = True
        return result
