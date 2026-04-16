from .dice_handler import DiceMixin
from .character_handler import CharacterMixin
from .coc_handler import CoCMixin
from .initiative_handler import InitiativeMixin
from .log_handler import LogMixin
from .llm_handler import LLMToolsMixin
from .router import RouterMixin


def _fix_handler_module_paths():
    """修补 Mixin 中装饰器方法的模块路径，使 Astrbot 框架能正确发现和绑定它们。

    Astrbot 通过 handler_module_path == plugin_module_path 精确匹配来查找 handler，
    但 Mixin 中定义的方法的 __module__ 指向 handler 子模块而非 main.py。
    此函数在所有 Mixin 导入完成后运行，将已注册的 handler 元数据的模块路径
    统一修正为插件主模块路径。
    """
    from astrbot.core.star.star_handler import star_handlers_registry
    from astrbot.core.provider.register import llm_tools

    # handler 子模块前缀，如 "xxx.handler."
    handler_prefix = __name__ + "."
    # 插件主模块路径，如 "xxx.main"
    main_module = __name__.rsplit(".handler", 1)[0] + ".main"

    # 修补普通 handler（command / event_message_type 等）
    for md in star_handlers_registry._handlers:
        if md.handler_module_path.startswith(handler_prefix):
            old_full_name = md.handler_full_name
            star_handlers_registry.star_handlers_map.pop(old_full_name, None)

            md.handler_module_path = main_module
            md.handler_full_name = f"{main_module}_{md.handler_name}"
            star_handlers_registry.star_handlers_map[md.handler_full_name] = md

    # 修补 LLM 工具 handler（框架直接检查 handler.__module__）
    for ft in llm_tools.func_list:
        handler = getattr(ft, "handler", None)
        if handler and getattr(handler, "__module__", "").startswith(handler_prefix):
            handler.__module__ = main_module
            if hasattr(ft, "handler_module_path"):
                ft.handler_module_path = main_module


_fix_handler_module_paths()
