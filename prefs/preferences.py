import bpy
import rna_keymap_ui
from .. import __ADDON_NAME__
from bpy.props import EnumProperty, StringProperty, FloatProperty, IntProperty, BoolProperty, PointerProperty, \
    FloatVectorProperty
from bpy.types import PropertyGroup


class GizmoMotionCamera(PropertyGroup):
    loop: BoolProperty(name="Loop", default=False)

    color: FloatVectorProperty(name='Color', subtype='COLOR_GAMMA', size=4,
                               default=(0.8, 0.0, 0.0, 0.6))
    color_highlight: FloatVectorProperty(name='Active Highlight', subtype='COLOR_GAMMA', size=4,
                                         default=(1, 0.0, 0.0, 0.8))
    scale_basis: FloatProperty(name='Scale', default=0.75, min=0.1)


class GizmoMotionSource(PropertyGroup):
    color: FloatVectorProperty(name='Color', subtype='COLOR_GAMMA', size=4,
                               default=(0.0, 0.6, 0.8, 0.6))
    color_highlight: FloatVectorProperty(name='Active Highlight', subtype='COLOR_GAMMA', size=4,
                                         default=(0.0, 0.8, 1.0, 0.8))
    scale_basis: FloatProperty(name='Scale', default=0.5, min=0.05)


class DrawMotionCurve(PropertyGroup):
    color: FloatVectorProperty(name='Color', subtype='COLOR_GAMMA', size=4, default=(0.8, 0, 0, 0.5))
    width: IntProperty(name='Width', default=3, min=1, soft_max=5)


class CAMHP_Preference(bpy.types.AddonPreferences):
    bl_idname = __ADDON_NAME__

    ui: EnumProperty(name='UI', items=[
        ('SETTINGS', 'Settings', '', 'PREFERENCES', 0),
        ('KEYMAP', 'Keymap', '', 'KEYINGSET', 1),
    ], default='SETTINGS')

    gz_motion_camera: PointerProperty(type=GizmoMotionCamera)
    gz_motion_source: PointerProperty(type=GizmoMotionSource)

    draw_motion_curve: PointerProperty(type=DrawMotionCurve)

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.prop(self, 'ui', expand=True)

        if self.ui == 'KEYMAP':
            self.draw_keymap(context, layout)
        elif self.ui == 'SETTINGS':
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

    def draw_keymap(self, context, layout):
        col = layout.box().column()
        col.label(text="Keymap", icon="KEYINGSET")
        km = None
        wm = context.window_manager
        kc = wm.keyconfigs.user

        old_km_name = ""
        get_kmi_l = []

        from .data_keymap import addon_keymaps

        for km_add, kmi_add in addon_keymaps:
            for km_con in kc.keymaps:
                if km_add.name == km_con.name:
                    km = km_con
                    break

            for kmi_con in km.keymap_items:
                if kmi_add.idname == kmi_con.idname and kmi_add.name == kmi_con.name:
                    get_kmi_l.append((km, kmi_con))

        get_kmi_l = sorted(set(get_kmi_l), key=get_kmi_l.index)

        for km, kmi in get_kmi_l:
            if not km.name == old_km_name:
                col.label(text=str(km.name), icon="DOT")

            col.context_pointer_set("keymap", km)
            rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)

            old_km_name = km.name


def register():
    bpy.utils.register_class(GizmoMotionCamera)
    bpy.utils.register_class(GizmoMotionSource)
    bpy.utils.register_class(DrawMotionCurve)
    bpy.utils.register_class(CAMHP_Preference)


def unregister():
    bpy.utils.unregister_class(CAMHP_Preference)
    bpy.utils.unregister_class(GizmoMotionCamera)
    bpy.utils.unregister_class(GizmoMotionSource)
    bpy.utils.unregister_class(DrawMotionCurve)
