from astrbot.api.event import filter, AstrMessageEvent

from ..component import dice as dice_mod
from ..component.output import get_output, get_config, get_config_int
from ..component.utils import get_sender_nickname


class DiceMixin:

    # @filter.command("r")
    async def handle_roll_dice(self, event: AstrMessageEvent, message: str = None, remark: str = None):
        """普通掷骰：改为直接调用 dice.handle_roll_dice，输出由 get_output 管理（无 fallback）"""

        message = message.strip() if message else None

        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        client = event.bot

        ret = await get_sender_nickname(client, group_id, user_id)
        ret = event.get_sender_name() if ret == "" else ret

        # 从配置获取默认骰子面数
        default_dice = get_config("dice.default_faces", 100)

        # 让 dice 模块处理表达式并返回由 get_output 格式化好的文本（或错误文本）
        result_text = dice_mod.handle_roll_dice(message if message else f"1d{default_dice}", name=ret, remark=remark)
        result_text = await self._beautify(result_text, event)
        message_id = event.message_obj.message_id
        payloads = {
            "group_id": group_id,
            "message": [
                {"type": "reply", "data": {"id": message_id}},
                {"type": "at", "data": {"qq": user_id}},
                {"type": "text", "data": {"text": "\n" + result_text}}
            ]
        }
        await self.save_log(group_id=event.get_group_id(), content=result_text)
        await client.api.call_action("send_group_msg", **payloads)

    @filter.command("rv")
    async def roll_dice_vampire(self, event: AstrMessageEvent, dice_count: str = "1", difficulty: str = "6"):
        """吸血鬼掷骰：使用 dice.roll_dice_vampire 得到内部结果，然后通过 get_output 输出模板文本（无 fallback）"""
        # 验证参数
        try:
            int_dice_count = int(dice_count)
            int_difficulty = int(difficulty)
        except ValueError:
            yield event.plain_result(get_output("dice.vampire.error", error="非法数值"))
            return

        max_count = get_config_int("dice.max_count", 100)
        if not (1 <= int_dice_count <= max_count):
            yield event.plain_result(get_output("dice.vampire.error", error=f"骰子数量须在 1-{max_count} 之间"))
            return
        if not (1 <= int_difficulty <= 10):
            yield event.plain_result(get_output("dice.vampire.error", error="难度须在 1-10 之间"))
            return

        result_body = dice_mod.roll_dice_vampire(int_dice_count, int_difficulty)

        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        client = event.bot

        ret = await get_sender_nickname(client, group_id, user_id)
        ret = event.get_sender_name() if ret == "" else ret
        text = get_output("dice.vampire.success", result=result_body, name=ret)
        text = await self._beautify(text, event)
        message_id = event.message_obj.message_id
        payloads = {
            "group_id": group_id,
            "message": [
                {"type": "reply", "data": {"id": message_id}},
                {"type": "at", "data": {"qq": user_id}},
                {"type": "text", "data": {"text": "\n" + text}}
            ]
        }
        await self.save_log(group_id=event.get_group_id(), content=text)
        await client.api.call_action("send_group_msg", **payloads)

    async def roll_hidden(self, event: AstrMessageEvent, message: str = None):
        """私聊发送掷骰结果 —— 所有文本由 get_output 管理（无 fallback）"""
        sender_id = event.get_sender_id()
        # 从配置获取默认骰子面数
        default_dice = get_config("dice.default_faces", 100)
        message = message.strip() if message else f"1d{default_dice}"

        notice_text = get_output("dice.hidden.group")
        yield event.plain_result(notice_text)

        private_text = dice_mod.roll_hidden(message)
        private_text = await self._beautify(private_text, event)

        # 发送私聊（使用平台 API）
        client = event.bot
        payloads = {
            "user_id": sender_id,
            "message": [
                {
                    "type": "text",
                    "data": {
                        "text": private_text
                    }
                }
            ]
        }

        await self.save_log(group_id=event.get_group_id(), content="[Private Roll Result]" + private_text)

        await client.api.call_action("send_private_msg", **payloads)
