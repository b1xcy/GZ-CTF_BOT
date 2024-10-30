from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config
from .gzbot import *

__plugin_meta__ = PluginMetadata(
    name="GZCTF_NOTICE_PLUGIN",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

