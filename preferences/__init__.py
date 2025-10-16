import bpy
import rna_keymap_ui
from .. import __package__ as base_package
from bpy.props import EnumProperty, StringProperty, FloatProperty, IntProperty, BoolProperty, PointerProperty, \
    FloatVectorProperty


class GizmoMotionCamera(bpy.types.PropertyGroup):
    loop: BoolProperty(name="Loop", default=False)

    color: FloatVectorProperty(name='Color', subtype='COLOR_GAMMA', size=4,
                               default=(0.8, 0.0, 0.0, 0.6))
    color_highlight: FloatVectorProperty(name='Active Highlight', subtype='COLOR_GAMMA', size=4,
                                         default=(1, 0.0, 0.0, 0.8))
    scale_basis: FloatProperty(name='Scale', default=1, min=0.2)


class GizmoMotionSource(bpy.types.PropertyGroup):
    color: FloatVectorProperty(name='Color', subtype='COLOR_GAMMA', size=4,
                               default=(0.0, 0.6, 0.8, 0.6))
    color_highlight: FloatVectorProperty(name='Active Highlight', subtype='COLOR_GAMMA', size=4,
                                         default=(0.0, 0.8, 1.0, 0.8))
    scale_basis: FloatProperty(name='Scale', default=0.75, min=0.1)


class DrawMotionCurve(bpy.types.PropertyGroup):
    color: FloatVectorProperty(name='Color', subtype='COLOR_GAMMA', size=4, default=(0.8, 0, 0, 0.5))
    width: IntProperty(name='Width', default=3, min=1, soft_max=5)


class CameraThumb(bpy.types.PropertyGroup):
    max_width: IntProperty(name='Max Width', default=400, min=50, soft_max=800)
    max_height: IntProperty(name='Max Height', default=300, min=50, soft_max=600)

    position: EnumProperty(name='Position', items=[
        ('TOP_LEFT', 'Top Left', ''),
        ('TOP_RIGHT', 'Top Right', ''),
        ('BOTTOM_LEFT', 'Bottom Left', ''),
        ('BOTTOM_RIGHT', 'Bottom Right', ''),
    ], default='TOP_LEFT')


class CAMHP_Preference(bpy.types.AddonPreferences):
    bl_idname = base_package


    gz_motion_camera: PointerProperty(type=GizmoMotionCamera)
    gz_motion_source: PointerProperty(type=GizmoMotionSource)

    draw_motion_curve: PointerProperty(type=DrawMotionCurve)

    camera_thumb: PointerProperty(type=CameraThumb)

    def draw(self, context):
        layout = self.layout
        self.draw_settings(context, layout)

    def draw_settings(self, context, layout):
        col = layout.column()
        col.use_property_split = True

        box = col.box().column(align=True)
        box.label(text='Motion Camera', icon='GIZMO')
        box.prop(self.gz_motion_camera, 'loop')
        box.prop(self.gz_motion_camera, 'color')
        box.prop(self.gz_motion_camera, 'color_highlight')
        box.prop(self.gz_motion_camera, 'scale_basis')

        box = col.box().column(align=True)
        box.label(text='Source', icon='GIZMO')
        box.prop(self.gz_motion_source, 'color', text='Color')
        box.prop(self.gz_motion_source, 'color_highlight')
        box.prop(self.gz_motion_source, 'scale_basis')

        box = col.box().column(align=True)
        box.label(text='Motion Curve', icon='CURVE_DATA')
        box.prop(self.draw_motion_curve, 'color')
        box.prop(self.draw_motion_curve, 'width', slider=True)

        box = col.box().column(align=True)
        box.label(text='Camera Thumbnails', icon='CAMERA_DATA')
        box.prop(self.camera_thumb, 'max_width', slider=True)
        box.prop(self.camera_thumb, 'max_height', slider=True)
        row = box.row(align=True)
        row.prop(self.camera_thumb, 'position', expand=True)


def register():
    bpy.utils.register_class(GizmoMotionCamera)
    bpy.utils.register_class(GizmoMotionSource)
    bpy.utils.register_class(DrawMotionCurve)
    bpy.utils.register_class(CameraThumb)
    bpy.utils.register_class(CAMHP_Preference)


def unregister():
    bpy.utils.unregister_class(CAMHP_Preference)
    bpy.utils.unregister_class(GizmoMotionCamera)
    bpy.utils.unregister_class(CameraThumb)
    bpy.utils.unregister_class(GizmoMotionSource)
    bpy.utils.unregister_class(DrawMotionCurve)
