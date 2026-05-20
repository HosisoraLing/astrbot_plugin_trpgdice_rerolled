import re
import random
import time

from astrbot.api.event import AstrMessageEvent
from astrbot.api.all import *

from ..component.output import get_config


class RouterMixin:

    # 识别所有信息
    @event_message_type(EventMessageType.GROUP_MESSAGE)
    async def identify_command(self, event: AstrMessageEvent):

        message = event.message_obj.message_str

         # ------------------- 日志收集逻辑 -------------------
        group_id = event.message_obj.group_id

        if group_id:
            user_id = event.message_obj.sender.user_id
            nickname = getattr(event.message_obj.sender, "nickname", "")
            timestamp = int(event.message_obj.timestamp)
            components = getattr(event.message_obj, "message", [])

            # 调用功能性模块添加消息
            await self.logger_core.add_message(
                group_id=group_id,
                user_id=user_id,
                nickname=nickname,
                timestamp=timestamp,
                text=message,
                components=components
            )
        # ----------------------------------------------------

        random.seed(int(time.time() * 1000))

        if not any(message.startswith(prefix) for prefix in self.wakeup_prefix):
            return

        message = re.sub(r'\s+', '', message[1:])

        m = re.match(r'^([a-z]+)', message, re.I)

        if not m:
            return

        cmd  = m.group(1).lower() if m else ""
        expr = message[m.end():].strip()
        remark = None

        skill_value = ""
        dice_count = "1"

        if cmd[0:2] == "en":
            sv_match = re.search(r'\d+$', message)
            if sv_match:
                skill_value = sv_match.group()
                expr = message[2:len(message)-len(skill_value)]
                cmd = "en"
            else:
                skill_value = None
                expr = message[2:]
                cmd = "en"
        if cmd[0:2] == "ra":
            sv_match = re.search(r'\d+$', message)
            if sv_match:
                skill_value = sv_match.group()
                expr = message[2:len(message)-len(skill_value)]
                cmd = "ra"
            else:
                skill_value = None
                expr = message[2:]
                cmd = "ra"

            if expr and (expr[0] == 'b' or expr[0] == 'p'):
                cmd = cmd + expr[0]
                expr = expr[1:]
                dice_count_match = re.search(r'\d+', expr)
                if dice_count_match:
                    dice_count = dice_count_match.group()
                    expr = expr[dice_count_match.end():]
                else:
                    dice_count = "1"

            if expr.isdigit():
                skill_value = expr

            if not expr and skill_value:
                expr = skill_value

        elif cmd[0:2] == "rd":
            raw = message[2:].strip()
            dice_match = re.match(r'(\d+)', raw)

            # 从配置获取默认骰子面数
            default_dice = get_config("dice.default_faces", 100)

            if dice_match:
                dice_size = dice_match.group(1)
                expr = f"1d{dice_size}"
                remark = raw[(len(dice_size)):].strip()[:100]
            else:
                expr = f"1d{default_dice}"
                remark = raw.strip()

        elif cmd[0] == "r":
            # 匹配完整的骰子表达式，包括运算符、保留最高(k)和数字（如 3d6+10, 10d6k5, 2d4-1d8 等）
            r_match = re.match(r'([0-9]*[dD][0-9]+(?:[kK]\d+)?(?:[+\-*][0-9]+(?:[dD][0-9]+)?)*)', message[1:])
            if r_match:
                expr = r_match.group(1)
                remark = message[1+len(expr):].strip()[:100]
            else:
                expr = message[1:].strip()
                # 如果没有指定骰子，使用默认骰子
                if not expr or not re.match(r'(\d*)[dD](\d+)', expr):
                    default_dice = get_config("dice.default_faces", 100)
                    expr = f"1d{default_dice}"

        if cmd == "r":
            await self.handle_roll_dice(event, expr, remark)
        elif cmd == "rd":
            await self.handle_roll_dice(event, expr, remark)
        elif cmd == "rh":
            async for result in self.roll_hidden(event):
                yield result
        elif cmd == "rab":
            await self.roll_attribute_bonus(event, dice_count, expr, skill_value)
        elif cmd == "rap":
            await self.roll_attribute_penalty(event, dice_count, expr, skill_value)
        elif cmd == "ra":
            await self.roll_attribute(event, expr, skill_value)
        elif cmd == "en":
            await self.pc_grow_up(event, expr, skill_value)
        elif cmd == "sc":
            async for result in self.pc_san_check(event, expr):
                yield result
        elif cmd == "li":
            async for result in self.pc_long_term_insanity(event):
                yield result
        elif cmd == "ti":
            async for result in self.pc_temporary_insanity(event):
                yield result
        elif cmd == "ri":
            async for result in self.roll_initiative(event, expr):
                yield result
