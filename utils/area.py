import bpy
from mathutils import Vector


def area_offset(context) -> Vector:
    """
        {'FOOTER',
        'ASSET_SHELF_HEADER',
         'NAVIGATION_BAR',
          'UI',
           'TOOL_HEADER',
            'ASSET_SHELF',
             'HEADER',
              'CHANNELS', 'HUD', 'TOOLS', 'EXECUTE', 'WINDOW'}
              """
    x = y = 0
    area = context.area
    if area is None:
        return Vector((x, y))
    for region in area.regions:
        if region.type == "TOOLS":
            x += region.width
        elif region.type == "HEADER":
            y += region.height
        elif region.type == "TOOL_HEADER":
            y += region.height
    return Vector((x, y))


def get_area_max_parent(area: bpy.types.Area):
    """如果当前area是最大化的
    则反回未最大化之前的area"""
    screen = bpy.context.screen
    if screen.show_fullscreen:
        if bpy.context.screen.name.endswith("-nonnormal"):  # 当前屏幕为最大化时，获取最大化之前的屏幕
            name = screen.name.replace("-nonnormal", "")
            screen = bpy.data.screens.get(name, None)
            if screen:
                for i in screen.areas:
                    if i.type == "EMPTY":
                        return i
    return area
