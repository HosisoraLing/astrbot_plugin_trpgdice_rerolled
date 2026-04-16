import re
import random

from astrbot.api.event import filter, AstrMessageEvent

from ..component.output import get_output, get_config

# 先攻表（模块级全局状态，按群组 ID 索引）
init_list = {}
current_index = {}


class InitiativeMixin:

    class InitiativeItem:
        def __init__(self, name: str, init_value: int, player_id: int):
            self.name = name
            self.init_value = init_value
            self.player_id = player_id  # 用于区分同名不同玩家

    def add_item(self, item, group_id: str):
        """添加先攻项并排序"""
        init_list[group_id].append(item)
        self.sort_list(group_id)

    def remove_by_name(self, name: str, group_id: str):
        """按名字删除先攻项"""
        try:
            init_list[group_id] = [item for item in init_list[group_id] if item.name != name]
        except KeyError:
            init_list[group_id] = []
            current_index[group_id] = 0

    def remove_by_player(self, player_id: int, group_id: str):
        """按玩家ID删除先攻项"""
        init_list[group_id] = [item for item in init_list[group_id] if item.player_id != player_id]

    def init_clear(self, group_id: str):
        """清空先攻表"""
        init_list[group_id].clear()
        current_index[group_id] = -1

    def sort_list(self, group_id: str):
        """按先攻值降序排序 (稳定排序)"""
        init_list[group_id].sort(key=lambda x: x.init_value, reverse=True)

    def next_turn(self, group_id: str):
        """移动到下一回合并返回当前项"""
        if not init_list[group_id]:
            return None

        if current_index[group_id] < 0:
            current_index[group_id] = 0
        else:
            current_index[group_id] = (current_index[group_id] + 1) % len(init_list[group_id])

        return init_list[group_id][current_index[group_id]]

    def format_list(self, group_id: str) -> str:
        """格式化先攻表输出"""
        try:
            fl = init_list[group_id]
        except KeyError:
            init_list[group_id] = []
            return "先攻列表为空"

        if not fl:
            return "先攻列表为空"

        lines = []
        for i, item in enumerate(fl):
            prefix = "-> " if i == current_index[group_id] else "   "
            lines.append(f"{prefix}{item.name}: {item.init_value}")
        return "\n".join(lines)

    @filter.command("init")
    async def initiative(self, event: AstrMessageEvent, instruction: str = None, player_name: str = None):
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        if not instruction:
            yield event.plain_result(get_output("initiative.current_list", content=self.format_list(group_id)))
        elif instruction == "clr":
            self.init_clear(group_id)
            yield event.plain_result(get_output("initiative.cleared"))
        elif instruction == "del":
            if not player_name:
                player_name = user_name
            self.remove_by_name(player_name, group_id)
            yield event.plain_result(get_output("initiative.deleted", player_name=player_name))

    # @filter.command("ri")
    async def roll_initiative(self, event: AstrMessageEvent, expr: str = None):

        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()

        # 从配置获取先攻掷骰范围
        dice_min = get_config("initiative.dice_range.min", 1)
        dice_max = get_config("initiative.dice_range.max", 20)

        if not expr:
            init_value = random.randint(dice_min, dice_max)
            player_name = user_name
        elif expr[0] == "+":
            match = re.match(r"\+(\d+)", expr)
            init_value = random.randint(dice_min, dice_max) + int(match.group(1))
            player_name = user_name
        elif expr[0] == "-":
            match = re.match(r"\-(\d+)", expr)
            init_value = random.randint(dice_min, dice_max) - int(match.group(1))
            player_name = user_name
        else:
            match = re.match(r"(\d+)", expr)
            init_value = int(match.group(1))
            player_name = expr[match.end():]
            if not player_name:
                player_name = user_name

        # 先攻值范围限制
        init_value = max(-9999, min(init_value, 9999))
        # 角色名长度限制
        player_name = player_name[:50].strip() or user_name

        item = self.InitiativeItem(player_name, init_value, user_id)
        self.remove_by_name(player_name, group_id)
        self.add_item(item, group_id)
        added_text = get_output("initiative.added", player_name=player_name, init_value=init_value)
        added_text = await self._beautify(added_text, event)
        yield event.plain_result(added_text)
        async for result in self.initiative(event):
            yield result

    @filter.command("ed")
    async def end_current_round(self, event: AstrMessageEvent):
        group_id = event.get_group_id()
        if group_id not in init_list or not init_list[group_id]:
            yield event.plain_result(get_output("initiative.empty_no_advance"))
            return
        if group_id not in current_index:
            current_index[group_id] = 0
        current_item = init_list[group_id][current_index[group_id]]
        next_item = self.next_turn(group_id)
        if not next_item:
            yield event.plain_result(get_output("initiative.empty_no_advance"))
        else:
            yield event.plain_result(get_output("initiative.turn_end", current_name=current_item.name, next_name=next_item.name, next_init=next_item.init_value))
