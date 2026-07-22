"""
平台适配器模块。

提供 ``BasePlatformAdapter`` 抽象基类及具体平台的实现。
通过 ``get_adapter(event)`` 工厂函数根据事件自动匹配合适的适配器。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BasePlatformAdapter
from .aiocqhttp import AiocqhttpAdapter
from .telegram import TelegramAdapter
from .qqofficial import QQOfficialAdapter
from .unknown import UnknownPlatformAdapter

if TYPE_CHECKING:
    from ..astrbot_compat import AstrMessageEvent

# ── 适配器注册表 ────────────────────────────────────────
# 在此注册新的平台适配器实例，工厂函数会按顺序匹配合适的适配器。
_BUILTIN_ADAPTERS: list[BasePlatformAdapter] = [
    AiocqhttpAdapter(),
    TelegramAdapter(),
    QQOfficialAdapter(),
]

# ── 公开 API ────────────────────────────────────────────

__all__ = [
    "BasePlatformAdapter",
    "AiocqhttpAdapter",
    "TelegramAdapter",
    "QQOfficialAdapter",
    "UnknownPlatformAdapter",
    "get_adapter",
    "register_adapter",
]


def get_adapter(event: AstrMessageEvent) -> BasePlatformAdapter:
    """根据事件来源平台返回匹配的适配器。

    遍历注册的适配器列表，返回第一个 ``matches_event()`` 返回 True 的适配器。
    如果没有找到匹配项，返回 ``UnknownPlatformAdapter``。
    """
    for adapter in _BUILTIN_ADAPTERS:
        if adapter.matches_event(event):
            return adapter
    return UnknownPlatformAdapter()


def register_adapter(adapter: BasePlatformAdapter) -> None:
    """注册一个新的平台适配器。

    Args:
        adapter: 平台适配器实例。``matches_event()`` 返回 True 时启用。
    """
    _BUILTIN_ADAPTERS.append(adapter)
