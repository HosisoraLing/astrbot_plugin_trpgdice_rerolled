"""
未知平台回退适配器。

对于尚无专用适配器的平台，提供最基础的文本交互：
  - 群消息：仅发送纯文本（无 reply / at）
  - 私聊：仅发送纯文本
  - 昵称：仅返回 event.get_sender_name()
  - 群名片：不支持
  - 撤回事件：不支持
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BasePlatformAdapter

if TYPE_CHECKING:
    from ..astrbot_compat import AstrMessageEvent


class UnknownPlatformAdapter(BasePlatformAdapter):
    """未知/默认平台的适配器，提供基础文本交互。"""

    def get_name(self) -> str:
        return "unknown"

    async def send_group_message(
        self,
        event: AstrMessageEvent,
        text: str,
        *,
        reply: bool = True,
    ) -> bool:
        # 回退适配器无法构造平台特定的 reply+at，返回 False 由调用方 fallback
        return False

    async def send_private_message(
        self,
        event: AstrMessageEvent,
        text: str,
    ) -> bool:
        return False

    async def get_nickname(
        self,
        event: AstrMessageEvent,
    ) -> str:
        return event.get_sender_name()
