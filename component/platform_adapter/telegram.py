"""
Telegram 平台适配器。

使用 python-telegram-bot 的 ExtBot API：
  - send_message（含 reply_to_message_id）
  - get_chat_member（获取群成员名称）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from telegram import ChatMember
from telegram.ext import ExtBot

from .base import BasePlatformAdapter

if TYPE_CHECKING:
    from ..astrbot_compat import AstrMessageEvent


class TelegramAdapter(BasePlatformAdapter):
    """Telegram 平台的适配器实现。"""

    def get_name(self) -> str:
        return "telegram"

    @property
    def supports_recall_events(self) -> bool:
        return False

    @property
    def supports_group_card(self) -> bool:
        return False

    # ── 工具方法 ──────────────────────────────────────────

    def _get_client(self, event: AstrMessageEvent) -> ExtBot:
        """获取 Telegram bot client。"""
        return cast(ExtBot, event.bot)

    def _get_chat_id(self, event: AstrMessageEvent) -> str:
        """获取消息来源的 chat_id。"""
        return event.get_group_id() or event.get_sender_id()

    # ── 消息发送 ──────────────────────────────────────────

    async def send_group_message(
        self,
        event: AstrMessageEvent,
        text: str,
        *,
        reply: bool = True,
    ) -> bool:
        client = self._get_client(event)
        chat_id = event.get_group_id()
        if not chat_id:
            return False

        payload: dict = {"chat_id": chat_id}

        # 回复原消息
        if reply and hasattr(event.message_obj, "message_id") and event.message_obj.message_id:
            payload["reply_to_message_id"] = int(event.message_obj.message_id)

        await client.send_message(text=text, **payload)
        return True

    async def send_private_message(
        self,
        event: AstrMessageEvent,
        text: str,
    ) -> bool:
        client = self._get_client(event)
        user_id = event.get_sender_id()
        if not user_id:
            return False

        await client.send_message(chat_id=user_id, text=text)
        return True

    # ── 用户信息 ──────────────────────────────────────────

    async def get_nickname(
        self,
        event: AstrMessageEvent,
    ) -> str:
        client = self._get_client(event)
        chat_id = event.get_group_id()
        user_id = event.get_sender_id()

        if chat_id and user_id:
            try:
                member: ChatMember = await client.get_chat_member(
                    chat_id=chat_id,
                    user_id=int(user_id),
                )
                user = member.user
                # Telegram 优先显示 first_name + last_name
                name_parts = [user.first_name or ""]
                if user.last_name:
                    name_parts.append(user.last_name)
                name = " ".join(name_parts).strip()
                if name:
                    return name
            except Exception:
                pass

        return event.get_sender_name()
