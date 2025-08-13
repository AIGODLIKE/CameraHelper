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
