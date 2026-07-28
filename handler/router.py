"""
消息路由与日志收集模块。

架构说明：
  AstrBot 中 @event_message_type 和 @filter.command 是互斥的调度链——
  一旦插件注册了 @event_message_type 处理器，@filter.command 就不会被调度。
  因此本插件将所有命令路由集中在 identify_command() 中处理，
  各 Mixin 类上的 @filter.command 装饰器仅作文档标注，不影响实际路由。
"""

import re

from ..component.astrbot_compat import AstrMessageEvent, filter, event_message_type, EventMessageType

from ..component.output import get_config
from ..component.platform_adapter import get_adapter

# 撤回事件的 notice_type
NOTICE_GROUP_RECALL = "group_recall"
NOTICE_FRIEND_RECALL = "friend_recall"


class RouterMixin:

    @filter.event_message_type(filter.EventMessageType.ALL, priority=100)
    async def handle_recall_event(self, event: AstrMessageEvent):
        """监听撤回事件，从日志中移除撤回的消息"""
        adapter = get_adapter(event)
        if not adapter.supports_recall_events:
            return
        try:
            raw = getattr(event.message_obj, "raw_message", None)
            if not raw:
                return

            post_type = raw.get("post_type") if isinstance(raw, dict) else getattr(raw, "post_type", None)
            if post_type not in (None, "notice"):
                return

            notice_type = raw.get("notice_type") if isinstance(raw, dict) else getattr(raw, "notice_type", None)
            if notice_type not in (NOTICE_GROUP_RECALL, NOTICE_FRIEND_RECALL):
                return

            recalled_msg_id = raw.get("message_id") if isinstance(raw, dict) else getattr(raw, "message_id", None)
            group_id = raw.get("group_id") if isinstance(raw, dict) else getattr(raw, "group_id", None)

            if recalled_msg_id and group_id:
                recalled_msg_id = str(recalled_msg_id)
                group_id = str(group_id)
                removed = await self.logger_core.remove_message_by_id(group_id, recalled_msg_id)
                if removed:
                    print(f"[TRPGDice] 已从日志中移除撤回的消息: {recalled_msg_id}")
        except Exception as e:
            print(f"[TRPGDice] 处理撤回事件出错: {e}")

    # 日志收集 + 全部命令路由（@event_message_type 在 AstrBot 中会先于 @filter.command 消费事件）
    @event_message_type(EventMessageType.ALL)
    async def identify_command(self, event: AstrMessageEvent):
        message = event.message_obj.message_str

        # ------------------- 日志收集 -------------------
        group_id = event.message_obj.group_id

        if group_id:
            user_id = event.message_obj.sender.user_id
            nickname = getattr(event.message_obj.sender, "nickname", "")
            timestamp = int(event.message_obj.timestamp)
            components = getattr(event.message_obj, "message", [])
            message_id = getattr(event.message_obj, "message_id", None)

            await self.logger_core.add_message(
                group_id=group_id,
                user_id=user_id,
                nickname=nickname,
                timestamp=timestamp,
                text=message,
                components=components,
                message_id=message_id
            )
        # ----------------------------------------------------

        if not any(message.startswith(prefix) for prefix in self.wakeup_prefix):
            return

        raw_message = message

        # 从原始消息（保留空格）中提取命令词，避免 "pc list" → "pclist" 的合并问题
        message_after_prefix = message[1:]
        m_space = re.match(r'^([a-z]+)', message_after_prefix, re.I)
        if not m_space:
            return
        cmd = m_space.group(1).lower()
        expr_raw = message_after_prefix[m_space.end():].strip()

        # 空格剔除版，用于 ra/en/rd/r 等复杂表达式的数值提取
        message = re.sub(r'\s+', '', message_after_prefix)
        m = re.match(r'^([a-z]+)', message, re.I)
        expr = message[m.end():].strip() if m else ""
        remark = None

        skill_value = ""
        dice_count = "1"

        # ===================== en =====================
        if cmd[0:2] == "en":
            sv_match = re.search(r'\d+$', message)
            if sv_match:
                skill_value = sv_match.group()
                expr = message[2:len(message) - len(skill_value)]
            else:
                skill_value = None
                expr = message[2:]

        # ===================== ra / rab / rap =====================
        if cmd[0:2] == "ra" and cmd not in ("rd", "rh"):
            sv_match = re.search(r'\d+$', message)
            if sv_match:
                skill_value = sv_match.group()
                expr = message[2:len(message) - len(skill_value)]
            else:
                skill_value = None
                expr = message[2:]

            if expr and (expr[0] == 'b' or expr[0] == 'p'):
                cmd = "ra" + expr[0]
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

        # ===================== rd =====================
        elif cmd[0:2] == "rd":
            raw_expr = message[2:].strip()
            dice_match = re.match(r'(\d+)', raw_expr)
            default_dice = get_config("dice.default_faces", 100)
            if dice_match:
                dice_size = dice_match.group(1)
                expr = f"1d{dice_size}"
                remark = raw_expr[len(dice_size):].strip()[:100]
            else:
                expr = f"1d{default_dice}"
                remark = raw_expr.strip()

        # ===================== r / rh =====================
        elif cmd[0] == "r":
            r_match = re.match(r'(\d+#[0-9]*[dD][0-9]+(?:[kK]\d+)?(?:[+\-*][0-9]+(?:[dD][0-9]+)?)*)', message[1:])
            if not r_match:
                r_match = re.match(r'([0-9]*[dD][0-9]+(?:[kK]\d+)?(?:[+\-*][0-9]+(?:[dD][0-9]+)?)*)', message[1:])
            if r_match:
                expr = r_match.group(1)
                remark = message[1 + len(expr):].strip()[:100]
            else:
                expr = message[1:].strip()
                if not expr or not re.match(r'(\d*)[dD](\d+)', expr):
                    default_dice = get_config("dice.default_faces", 100)
                    expr = f"1d{default_dice}"

        # ===================== 命令分发 =====================
        # --- 掷骰 ---
        if cmd == "r":
            text = await self.handle_roll_dice(event, expr, remark)
            if text:
                adapter = get_adapter(event)
                sent = await adapter.send_group_message(event, text, reply=True)
                if not sent:
                    yield event.plain_result(text)
        elif cmd == "rd":
            text = await self.handle_roll_dice(event, expr, remark)
            if text:
                adapter = get_adapter(event)
                sent = await adapter.send_group_message(event, text, reply=True)
                if not sent:
                    yield event.plain_result(text)
        elif cmd == "rh":
            async for result in self.roll_hidden(event, expr if expr else None):
                yield result

        # --- COC 技能 ---
        elif cmd == "ra":
            if not expr_raw:
                yield event.plain_result("[错误] 用法: .ra 技能名 [技能值]")
                return
            text = await self.roll_attribute(event, expr_raw, skill_value)
            if text:
                adapter = get_adapter(event)
                sent = await adapter.send_group_message(event, text, reply=True)
                if not sent:
                    yield event.plain_result(text)
        elif cmd == "rab":
            if not expr_raw:
                yield event.plain_result("[错误] 用法: .rab [n] 技能名 [技能值]")
                return
            text = await self.roll_attribute_bonus(event, dice_count, expr_raw, skill_value)
            if text:
                adapter = get_adapter(event)
                sent = await adapter.send_group_message(event, text, reply=True)
                if not sent:
                    yield event.plain_result(text)
        elif cmd == "rap":
            if not expr_raw:
                yield event.plain_result("[错误] 用法: .rap [n] 技能名 [技能值]")
                return
            text = await self.roll_attribute_penalty(event, dice_count, expr_raw, skill_value)
            if text:
                adapter = get_adapter(event)
                sent = await adapter.send_group_message(event, text, reply=True)
                if not sent:
                    yield event.plain_result(text)
        elif cmd == "en":
            if not expr_raw:
                yield event.plain_result("[错误] 用法: .en 技能名 [技能值]")
                return
            text = await self.pc_grow_up(event, expr_raw, skill_value)
            if text:
                adapter = get_adapter(event)
                sent = await adapter.send_group_message(event, text, reply=True)
                if not sent:
                    yield event.plain_result(text)

        # --- 理智 ---
        elif cmd == "sc":
            # 兼容三种输入格式：
            #   .sc 1d3/1d9 → 标准格式，成功扣1d3，失败扣1d9
            #   .sc 1d3 1d9 → 空格分隔，等同 "/"
            #   .sc 1d9     → 仅指定失败损失，成功不扣 san
            if not expr_raw:
                sc_formula = "1d6/1d10"
                yield event.plain_result("⚠️ 未指定理智损失公式，将使用默认值：成功扣 1d6 / 失败扣 1d10")
            elif "/" in expr_raw:
                sc_formula = expr_raw
            elif " " in expr_raw.strip():
                parts = expr_raw.strip().split(None, 1)
                sc_formula = f"{parts[0]}/{parts[1]}"
            else:
                # 仅一个值：成功不扣，失败扣该值
                sc_formula = f"0/{expr_raw}"
            async for result in self.pc_san_check(event, sc_formula):
                yield result
        elif cmd == "ti":
            async for result in self.pc_temporary_insanity(event):
                yield result
        elif cmd == "li":
            async for result in self.pc_long_term_insanity(event):
                yield result

        # --- 先攻 ---
        elif cmd == "ri":
            async for result in self.roll_initiative(event, expr_raw if expr_raw else None):
                yield result
        elif cmd == "init":
            sub_expr = expr_raw.lower() if expr_raw else ""
            if not sub_expr:
                async for result in self.initiative(event, None, None):
                    yield result
            elif sub_expr == "clr":
                async for result in self.initiative(event, "clr", None):
                    yield result
            elif sub_expr.startswith("del"):
                name = sub_expr[3:].strip() if len(sub_expr) > 3 else ""
                async for result in self.initiative(event, "del", name if name else None):
                    yield result
            else:
                async for result in self.initiative(event, None, None):
                    yield result
        elif cmd == "ed":
            async for result in self.end_current_round(event):
                yield result

        # --- 杂项 ---
        elif cmd == "coc":
            try:
                x = int(expr_raw) if expr_raw else 1
            except ValueError:
                x = 1
            async for result in self.generate_coc_character(event, x):
                yield result
        elif cmd == "dnd":
            try:
                x = int(expr_raw) if expr_raw else 1
            except ValueError:
                x = 1
            async for result in self.generate_dnd_character(event, x):
                yield result
        elif cmd == "dicehelp":
            async for result in self.help(event):
                yield result
        elif cmd == "fireball":
            try:
                ring = int(expr_raw) if expr_raw else 3
            except ValueError:
                yield event.plain_result("[错误] 用法: .fireball [环位] (3-20)")
                return
            async for result in self.fireball_cmd(event, ring):
                yield result
        elif cmd == "jrrp":
            async for result in self.roll_RP_cmd(event):
                yield result
        elif cmd == "setcoc":
            async for result in self.setcoc_cmd(event, expr_raw if expr_raw else " "):
                yield result

        # --- 人物卡属性 ---
        elif cmd == "st":
            parts = raw_message[1:].strip().split(maxsplit=1)
            if len(parts) >= 2:
                attrs = parts[1]
                attr_parts = attrs.split(maxsplit=1)
                async for result in self.status(event, attr_parts[0] if len(attr_parts) >= 1 else "", attr_parts[1] if len(attr_parts) >= 2 else ""):
                    yield result
            else:
                yield event.plain_result("[错误] 用法: .st 属性名[+/-/*]值  (如 .st san+5 或 .st hp+2d6)")
        elif cmd == "sn":
            async for result in self.filter_set_nickname(event):
                yield result

        # --- 人物卡管理 (pc) ---
        elif cmd == "pc":
            pc_parts = raw_message[1:].strip().split(maxsplit=2)
            sub_cmd = pc_parts[1].strip().lower() if len(pc_parts) >= 2 else ""
            rest = pc_parts[2] if len(pc_parts) >= 3 else ""

            if sub_cmd == "create":
                rest_parts = rest.split(maxsplit=1)
                name = rest_parts[0] if rest_parts else None
                attrs = rest_parts[1] if len(rest_parts) >= 2 else ""
                if not name:
                    yield event.plain_result("[错误] 用法: .pc create <名称> [属性值]")
                    return
                async for result in self.pc_create_character(event, name, attrs):
                    yield result
            elif sub_cmd == "show":
                attr_name = rest if rest else None
                async for result in self.pc_show_character(event, attr_name):
                    yield result
            elif sub_cmd == "list":
                async for result in self.pc_list_characters(event):
                    yield result
            elif sub_cmd == "change":
                if not rest:
                    yield event.plain_result("[错误] 用法: .pc change <名称>")
                    return
                async for result in self.pc_change_character(event, rest):
                    yield result
            elif sub_cmd == "update":
                upd_parts = rest.split(maxsplit=1)
                attr = upd_parts[0] if upd_parts else ""
                val = upd_parts[1] if len(upd_parts) >= 2 else ""
                if not attr:
                    yield event.plain_result("[错误] 用法: .pc update <属性名> <值/公式>")
                    return
                async for result in self.pc_update_character(event, attr, val):
                    yield result
            elif sub_cmd == "delete":
                if not rest:
                    yield event.plain_result("[错误] 用法: .pc delete <名称>")
                    return
                async for result in self.pc_delete_character(event, rest):
                    yield result
            else:
                yield event.plain_result("[提示] pc 子命令: create / show / list / change / update / delete")

        # --- 日志管理 (log) ---
        elif cmd == "log":
            log_parts = raw_message[1:].strip().split(maxsplit=1)
            sub_cmd = log_parts[1].strip().lower() if len(log_parts) >= 2 else ""

            if sub_cmd.startswith("new"):
                async for result in self.cmd_log_new(event):
                    yield result
            elif sub_cmd.startswith("end"):
                async for result in self.cmd_log_end(event):
                    yield result
            elif sub_cmd.startswith("off"):
                async for result in self.cmd_log_off(event):
                    yield result
            elif sub_cmd.startswith("on"):
                async for result in self.cmd_log_on(event):
                    yield result
            elif sub_cmd.startswith("list"):
                async for result in self.cmd_log_list(event):
                    yield result
            elif sub_cmd.startswith("del"):
                parts_check = raw_message[1:].strip().split()
                if len(parts_check) < 3:
                    yield event.plain_result("[错误] 用法: .log del <日志名>")
                    return
                async for result in self.cmd_log_del(event):
                    yield result
            elif sub_cmd.startswith("get"):
                parts_check = raw_message[1:].strip().split()
                if len(parts_check) < 3:
                    yield event.plain_result("[错误] 用法: .log get <日志名>")
                    return
                async for result in self.cmd_log_get(event):
                    yield result
            elif sub_cmd.startswith("stat"):
                async for result in self.cmd_log_stat(event):
                    yield result
            else:
                yield event.plain_result("[提示] log 子命令: new / on / off / end / list / del / get / stat")
