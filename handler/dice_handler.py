"""
掷骰命令处理 Mixin。

注意：本文件中的 @filter.command 装饰器在当前 AstrBot 版本中不会被调度
（事件已被 RouterMixin.identify_command 消费），保留仅作文档标注和向前兼容。
实际命令路由见 handler/router.py。
"""

from ..component.astrbot_compat import filter, AstrMessageEvent

from ..component import dice as dice_mod
from ..component.output import get_output, get_config
from ..component.platform_adapter import get_adapter


class DiceMixin:

    @filter.command("r")
    async def cmd_r(self, event: AstrMessageEvent, expr: str = "", remark: str = ""):
        """普通掷骰 (.r 1d100 备注)"""
        expr = expr.strip() if expr else None
        remark = remark.strip() if remark else None
        text = await self.handle_roll_dice(event, expr, remark)
        yield event.plain_result(text)

    @filter.command("rd")
    async def cmd_rd(self, event: AstrMessageEvent, dice_size: str = "", remark: str = ""):
        """简化掷骰 (.rd 100 备注 或 .rd 备注)"""
        default_dice = get_config("dice.default_faces", 100)
        if dice_size and dice_size.isdigit():
            expr = f"1d{dice_size}"
        else:
            expr = f"1d{default_dice}"
            # 如果 dice_size 不是数字，整体当作备注
            if dice_size:
                remark = f"{dice_size} {remark}".strip()
        remark = remark.strip() if remark else None
        text = await self.handle_roll_dice(event, expr, remark)
        yield event.plain_result(text)

    async def handle_roll_dice(self, event: AstrMessageEvent, message: str = None, remark: str = None) -> str:
        """普通掷骰，返回结果文本（由调用方负责平台发送）。"""
        message = message.strip() if message else None

        adapter = get_adapter(event)
        name = await adapter.get_nickname(event)

        default_dice = get_config("dice.default_faces", 100)

        result_text = dice_mod.handle_roll_dice(message if message else f"1d{default_dice}", name=name, remark=remark)
        result_text = await self._beautify(result_text, event)
        await self.save_log(group_id=event.get_group_id(), content=result_text)

        return result_text

    @filter.command("rh")
    async def roll_hidden(self, event: AstrMessageEvent, message: str = None):
        """私聊发送掷骰结果"""
        adapter = get_adapter(event)
        default_dice = get_config("dice.default_faces", 100)
        message = message.strip() if message else f"1d{default_dice}"

        notice_text = get_output("dice.hidden.group")
        yield event.plain_result(notice_text)

        private_text = dice_mod.roll_hidden(message)
        private_text = await self._beautify(private_text, event)

        await self.save_log(group_id=event.get_group_id(), content="[Private Roll Result]" + private_text)

        sent = await adapter.send_private_message(event, private_text)
        if not sent:
            yield event.plain_result(private_text)
