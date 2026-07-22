"""
平台适配器抽象基类。

定义所有平台适配器必须实现的接口。
各平台的具体实现在本模块的子模块中。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..astrbot_compat import AstrMessageEvent


class BasePlatformAdapter(ABC):
    """平台适配器抽象基类。

    每个平台适配器封装了特定平台的消息发送、用户信息获取等操作，
    使上层 handler 无需直接调用平台特定的 API。
    """

    # ── 平台识别 ──────────────────────────────────────────

    @abstractmethod
    def get_name(self) -> str:
        """返回平台类型名称，例如 'aiocqhttp'、'telegram'。"""
        ...

    def matches_event(self, event: AstrMessageEvent) -> bool:
        """判断此适配器是否能处理给定事件所在平台。

        默认比较 ``event.get_platform_name()`` 与 ``get_name()``。
        """
        return event.get_platform_name() == self.get_name()

    # ── 能力声明 ──────────────────────────────────────────

    @property
    def supports_recall_events(self) -> bool:
        """是否支持监听消息撤回事件。"""
        return False

    @property
    def supports_group_card(self) -> bool:
        """是否支持修改群名片/昵称。"""
        return False

    # ── 消息发送 ──────────────────────────────────────────

    @abstractmethod
    async def send_group_message(
        self,
        event: AstrMessageEvent,
        text: str,
        *,
        reply: bool = True,
    ) -> bool:
        """向事件来源群发送文本消息。

        Args:
            event: 原始消息事件。
            text: 要发送的文本。
            reply: 是否回复原始消息并 @ 发送者。

        Returns:
            True 表示消息已成功发送；False 表示此适配器不支持该操作，
            调用方应回退到 ``yield event.plain_result(text)``。
        """
        ...

    @abstractmethod
    async def send_private_message(
        self,
        event: AstrMessageEvent,
        text: str,
    ) -> bool:
        """向事件发送者私聊发送文本消息。

        Returns:
            True 表示发送成功；False 表示此适配器不支持该操作。
        """
        ...

    # ── 用户信息 ──────────────────────────────────────────

    @abstractmethod
    async def get_nickname(
        self,
        event: AstrMessageEvent,
    ) -> str:
        """获取事件发送者在当前群组中的显示名称。

        Returns:
            显示名称。如果无法获取，返回 ``event.get_sender_name()`` 的值。
        """
        ...

    # ── 群组管理 ──────────────────────────────────────────

    async def set_group_card(
        self,
        event: AstrMessageEvent,
        card: str,
    ) -> bool:
        """修改发送者的群名片。

        Returns:
            是否成功执行。默认返回 False 表示不支持。
        """
        return False
