import bpy
import blf

from bpy.types import Operator
from bpy.props import EnumProperty, StringProperty

from mathutils import Vector
from math import tan, radians, sqrt

from .utils import Cam
from .draw_utils.shader import wrap_blf_size, ui_scale




class pop_cam_panel(bpy.types.Panel):
    """Properties"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'


class CAMHP_PT_pop_cam_comp_panel(pop_cam_panel):
    bl_label = "Composition Guides"
    bl_idname = 'CAMHP_PT_pop_cam_comp_panel'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        cam = context.scene.camera.data

        layout.prop(cam, "show_composition_thirds")

        col = layout.column(heading="Center", align=True)
        col.prop(cam, "show_composition_center")
        col.prop(cam, "show_composition_center_diagonal", text="Diagonal")

        col = layout.column(heading="Golden", align=True)
        col.prop(cam, "show_composition_golden", text="Ratio")
        col.prop(cam, "show_composition_golden_tria_a", text="Triangle A")
        col.prop(cam, "show_composition_golden_tria_b", text="Triangle B")

        col = layout.column(heading="Harmony", align=True)
        col.prop(cam, "show_composition_harmony_tri_a", text="Triangle A")
        col.prop(cam, "show_composition_harmony_tri_b", text="Triangle B")


class CAMHP_PT_pop_cam_dof(pop_cam_panel):
    bl_label = "Depth of Field"
    bl_idname = 'CAMHP_PT_pop_cam_dof'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        cam = context.scene.camera.data

        dof = cam.dof
        layout.prop(dof, "use_dof")
        layout.active = dof.use_dof

        col = layout.column()
        col.prop(dof, "focus_object", text="Focus on Object")
        sub = col.column()
        sub.active = (dof.focus_object is None)
        sub.prop(dof, "focus_distance", text="Focus Distance")

        flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=False)

        col = flow.column()
        col.prop(dof, "aperture_fstop")

        col = flow.column()
        col.prop(dof, "aperture_blades")
        col.prop(dof, "aperture_rotation")
        col.prop(dof, "aperture_ratio")


class CAMHP_PT_pop_cam_lens(pop_cam_panel):
    bl_label = "Lens"
    bl_idname = 'CAMHP_PT_pop_cam_lens'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        cam = context.scene.camera.data

        layout.prop(cam, "type")

        col = layout.column()
        col.separator()

        if cam.type == 'PERSP':
            if cam.lens_unit == 'MILLIMETERS':
                col.prop(cam, "lens")
            elif cam.lens_unit == 'FOV':
                col.prop(cam, "angle")
            col.prop(cam, "lens_unit")

        elif cam.type == 'ORTHO':
            col.prop(cam, "ortho_scale")

        elif cam.type == 'PANO':
            engine = context.engine
            if engine == 'CYCLES':
                ccam = cam.cycles
                col.prop(ccam, "panorama_type")
                if ccam.panorama_type == 'FISHEYE_EQUIDISTANT':
                    col.prop(ccam, "fisheye_fov")
                elif ccam.panorama_type == 'FISHEYE_EQUISOLID':
                    col.prop(ccam, "fisheye_lens", text="Lens")
                    col.prop(ccam, "fisheye_fov")
                elif ccam.panorama_type == 'EQUIRECTANGULAR':
                    sub = col.column(align=True)
                    sub.prop(ccam, "latitude_min", text="Latitude Min")
                    sub.prop(ccam, "latitude_max", text="Max")
                    sub = col.column(align=True)
                    sub.prop(ccam, "longitude_min", text="Longitude Min")
                    sub.prop(ccam, "longitude_max", text="Max")
                elif ccam.panorama_type == 'FISHEYE_LENS_POLYNOMIAL':
                    col.prop(ccam, "fisheye_fov")
                    col.prop(ccam, "fisheye_polynomial_k0", text="K0")
                    col.prop(ccam, "fisheye_polynomial_k1", text="K1")
                    col.prop(ccam, "fisheye_polynomial_k2", text="K2")
                    col.prop(ccam, "fisheye_polynomial_k3", text="K3")
                    col.prop(ccam, "fisheye_polynomial_k4", text="K4")

            elif engine in {'BLENDER_RENDER', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'}:
                if cam.lens_unit == 'MILLIMETERS':
                    col.prop(cam, "lens")
                elif cam.lens_unit == 'FOV':
                    col.prop(cam, "angle")
                col.prop(cam, "lens_unit")

        col = layout.column()
        col.separator()

        sub = col.column(align=True)
        sub.prop(cam, "shift_x", text="Shift X")
        sub.prop(cam, "shift_y", text="Y")

        col.separator()
        sub = col.column(align=True)
        sub.prop(cam, "clip_start", text="Clip Start")
        sub.prop(cam, "clip_end", text="End")


class CAMHP_OT_popup_cam_settings(Operator):
    """Properties"""
    bl_idname = 'camhp.popup_cam_settings'
    bl_label = 'Camera Settings'

    def invoke(self, context, event):
        def draw(self_, context_):
            layout = self_.layout
            layout.popover(panel='CAMHP_PT_pop_cam_lens')
            layout.popover(panel='CAMHP_PT_pop_cam_dof')
            layout.popover(panel='CAMHP_PT_pop_cam_comp_panel', text='Guide')

        context.window_manager.popup_menu(draw, title=context.scene.camera.name)
        return {'INTERFACE'}




def register():

    bpy.utils.register_class(CAMHP_PT_pop_cam_comp_panel)
    bpy.utils.register_class(CAMHP_PT_pop_cam_dof)
    bpy.utils.register_class(CAMHP_PT_pop_cam_lens)
    bpy.utils.register_class(CAMHP_OT_popup_cam_settings)


def unregister():

    bpy.utils.unregister_class(CAMHP_PT_pop_cam_comp_panel)
    bpy.utils.unregister_class(CAMHP_PT_pop_cam_dof)
    bpy.utils.unregister_class(CAMHP_PT_pop_cam_lens)
    bpy.utils.unregister_class(CAMHP_OT_popup_cam_settings)
