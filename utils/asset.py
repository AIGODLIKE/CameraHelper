from enum import Enum
from pathlib import Path


class AssetDir(Enum):
    ASSET_BLEND = 'CamerHelper.blend'
    ASSET_BLEND_WITH_GIZMO = 'CamerHelperWithGizmo.blend'


def get_asset_dir(subpath=None):
    """custom dir"""
    preset_dir = Path(__file__).parent.parent.joinpath("res", "asset")

    print("get_asset_dir", preset_dir)
    if subpath in [item.value for item in AssetDir]:
        return preset_dir.joinpath(subpath)

    return preset_dir
