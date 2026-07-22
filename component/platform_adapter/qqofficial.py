"""
QQ 官方机器人 (qq_official) 平台适配器。

使用 qq-botpy 库的 Client API：
  - bot.api.post_group_message() 发送群消息
  - /v2/users/{openid}/messages   发送 C2C 消息
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from botpy.http import Route

from .base import BasePlatformAdapter

if TYPE_CHECKING:
    from ..astrbot_compat import AstrMessageEvent


class QQOfficialAdapter(BasePlatformAdapter):
    """QQ 官方机器人平台的适配器实现。"""

    def get_name(self) -> str:
        return "qq_official"

    @property
    def supports_recall_events(self) -> bool:
        return False

    @property
    def supports_group_card(self) -> bool:
        return False

    # ── 工具方法 ──────────────────────────────────────────

    def _get_openid(self, event: AstrMessageEvent) -> str | None:
        """从原始消息中提取 user_openid（C2C 私聊用）。"""
        raw = event.message_obj.raw_message
        author = getattr(raw, "author", None)
        if author is None:
            return None
        return getattr(author, "user_openid", None) or None

    # ── 消息发送 ──────────────────────────────────────────

    async def send_group_message(
        self,
        event: AstrMessageEvent,
        text: str,
        *,
        reply: bool = True,
    ) -> bool:
        client = event.bot
        group_id = event.get_group_id()
        if not group_id:
            return False

        payload: dict[str, Any] = {
            "content": text,
            "msg_type": 0,
        }

        # msg_id：被动回复时传入，使消息以回复形式展示
        if reply and hasattr(event.message_obj, "message_id") and event.message_obj.message_id:
            payload["msg_id"] = event.message_obj.message_id

        # msg_seq：主动/被动发送都需要
        payload["msg_seq"] = random.randint(1, 10000)

        try:
            await client.api.post_group_message(
                group_openid=group_id,
                **payload,
            )
            return True
        except Exception:
            return False

    async def send_private_message(
        self,
        event: AstrMessageEvent,
        text: str,
    ) -> bool:
        client = event.bot
        openid = self._get_openid(event)
        if not openid:
            return False

        payload: dict[str, Any] = {
            "content": text,
            "msg_type": 0,
            "msg_seq": random.randint(1, 10000),
        }

        try:
            route = Route("POST", f"/v2/users/{openid}/messages")
            await client.api._http.request(route, json=payload)
            return True
        except Exception:
            return False

    # ── 用户信息 ──────────────────────────────────────────

    async def get_nickname(
        self,
        event: AstrMessageEvent,
    ) -> str:
        """QQ 官方机器人不提供便捷的群昵称查询接口，返回发送者名称。"""
        return event.get_sender_name()
