from enum import Enum
from pathlib import Path


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

