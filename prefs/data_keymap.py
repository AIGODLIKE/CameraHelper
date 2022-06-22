import bpy

addon_keymaps = []


def register():
    wm = bpy.context.window_manager
    if not wm.keyconfigs.addon: return
    # 双击点开材质
    # km = wm.keyconfigs.addon.keymaps.new(name='File Browser', space_type='FILE_BROWSER')
    # kmi = km.keymap_items.new("mathp.edit_material_asset", 'LEFTMOUSE', 'DOUBLE_CLICK', ctrl=False, shift=False)
    # addon_keymaps.append((km, kmi))




def unregister():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc: return

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)

    addon_keymaps.clear()
