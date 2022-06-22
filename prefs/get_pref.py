import bpy
from .. import __ADDON_NAME__


def get_pref():
    """get preferences of this plugin"""
    return bpy.context.preferences.addons.get(__ADDON_NAME__).preferences
