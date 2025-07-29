from enum import Enum
from pathlib import Path

import bpy


def get_pref():
    """get preferences of this plugin"""
    return bpy.context.preferences.addons[__package__].preferences


class AssetDir(Enum):
    DIRECTORY = 'asset'
    ASSET_BLEND = 'CamerHelper.blend'
    ASSET_BLEND_WITH_GIZMO = 'CamerHelperWithGizmo.blend'


def get_asset_dir(subpath=None):
    """custom dir"""
    preset_dir = Path(__file__).parent.joinpath(AssetDir.DIRECTORY.value)

    # if subpath in ResourceDir enum value
    if subpath in [item.value for item in AssetDir]:
        return preset_dir.joinpath(subpath)

    return preset_dir


def offset_2d_gizmo(context, gizmo, offset_step):
    # ui scale
    ui_scale = bpy.context.preferences.system.dpi * (1 / 72)
    region = context.region

    step = 30 * ui_scale
    icon_scale = (80 * 0.35) / 2  # 14
    # 从屏幕右侧起
    start_x = region.width - (icon_scale * ui_scale + step) / 2
    start_y = region.height

    # 检查是否启用区域重叠，若启用则加上宽度以符合侧面板移动
    if context.preferences.system.use_region_overlap:
        for region in context.area.regions:
            if region.type == 'UI':
                start_x -= region.width
            elif region.type == 'HEADER':
                start_y -= region.height

    # 检查是否开启坐标轴
    if context.preferences.view.mini_axis_type == 'MINIMAL':
        size = context.preferences.view.mini_axis_size * ui_scale * 2  # 获取实际尺寸 此尺寸需要乘2
        start_y -= size + step * 2  #
    elif context.preferences.view.mini_axis_type == 'GIZMO':
        size = context.preferences.view.gizmo_size_navigate_v3d * ui_scale * 1.2  # 获取实际尺寸 此尺寸需要乘1.2
        start_y -= size + step * 2  #
    elif context.preferences.view.mini_axis_type == 'NONE':
        start_y -= step * 2

        # 检查是否开启默认控件
    if context.preferences.view.show_navigate_ui:
        start_y -= (icon_scale * ui_scale + step) * 3
    else:
        start_y -= step * 2 * ui_scale

    gizmo.matrix_basis[0][3] = start_x
    gizmo.matrix_basis[1][3] = start_y - step * offset_step
    gizmo.scale_basis = icon_scale