import re
from typing import Optional

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.all import *

from ..component import character as charmod
from ..component import dice as dice_mod
from ..component.output import get_output


def _parse_value_expr(value_expr):
    if not value_expr:
        return 0, ""
    if 'd' in value_expr.lower():
        dice_match = re.match(r"(\d*)d(\d+)", value_expr.lower())
        if dice_match:
            dice_count = int(dice_match.group(1)) if dice_match.group(1) else 1
            dice_faces = int(dice_match.group(2))
            rolls = dice_mod.roll_dice(dice_count, dice_faces)
            return sum(rolls), get_output("dice.detail", detail=f"[{' + '.join(map(str, rolls))}] = {sum(rolls)}")
        return None, ""
    try:
        return int(value_expr), ""
    except ValueError:
        return None, ""


class CharacterMixin:

    async def _apply_attribute_change(self, event, user_id, chara_id, attribute, operator, value_num, roll_detail=""):
        chara_data = charmod.load_character(user_id, chara_id)
        if not chara_data:
            return None, get_output("pc.show.load_fail", id=chara_id)

        if attribute not in chara_data["attributes"]:
            chara_data["attributes"][attribute] = 0

        current_value = chara_data["attributes"][attribute]

        if operator == "+":
            new_value = current_value + value_num
        elif operator == "-":
            new_value = current_value - value_num
        elif operator == "*":
            new_value = current_value * value_num
        else:
            new_value = value_num

        chara_data["attributes"][attribute] = max(0, new_value)
        charmod.save_character(user_id, chara_id, chara_data)

        text = get_output("pc.update.success", attr=attribute, old=current_value, new=new_value)
        if roll_detail:
            text += "\n" + roll_detail

        await self.save_log(group_id=event.get_group_id(), content=text)
        return text, None

    @filter.command("st")
    async def status(self, event: AstrMessageEvent, attributes: str = None, exp: str = None):
        if not attributes:
            return

        user_id = event.get_sender_id()
        chara_id = charmod.get_current_character_id(user_id)
        if not chara_id:
            yield event.plain_result(get_output("pc.show.no_active"))
            return

        full_expr = (str(attributes) if attributes else "") + (str(exp) if exp else "")
        attributes_clean = re.sub(r'\s+', '', full_expr)

        match = re.match(r"([\u4e00-\u9fa5a-zA-Z]+)\s*([+\-*]?)\s*(\d+(?:d\d+)?|\d*)", attributes_clean)
        if not match:
            yield event.plain_result(get_output("pc.show.attr_missing", attribute=attributes_clean))
            return

        attribute = match.group(1)
        operator = match.group(2) if match.group(2) else None
        value_expr = match.group(3) if match.group(3) else None

        chara_data = charmod.load_character(user_id, chara_id)
        if attribute not in chara_data["attributes"]:
            yield event.plain_result(get_output("pc.show.attr_missing", attribute=attribute))
            return

        value_num, roll_detail = _parse_dice_expr(value_expr)
        if value_num is None:
            yield event.plain_result(get_output("pc.show.invalid_value", value=value_expr))
            return

        text, error = await self._apply_attribute_change(event, user_id, chara_id, attribute, operator, value_num, roll_detail)
        if error:
            yield event.plain_result(error)
            return

        yield event.plain_result(text)

    @command_group("pc")
    def pc(self):
        pass

    @pc.command("create")
    async def pc_create_character(self, event, name: Optional[str] = None, attributes: str = ""):
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        characters = charmod.get_all_characters(user_id)

        name = charmod.sanitize_name(name or user_name or "调查员")

        if name in characters:
            yield event.plain_result(get_output("pc.create.duplicate", name=name))
            return

        initial_data = (
            "力量0str0敏捷0dex0意志0pow0体质0con0外貌0app0教育0知识0edu0"
            "体型0siz0智力0灵感0int0san0san值0理智0理智值0幸运0运气0mp0魔法0hp0"
            "体力0会计5人类学1估价5考古学1取悦15攀爬20计算机5计算机使用5电脑5"
            "信用0信誉0信用评级0克苏鲁0克苏鲁神话0cm0乔装5闪避0汽车20驾驶20汽车驾驶20"
            "电气维修10电子学1话术5斗殴25手枪20急救30历史5恐吓15跳跃20拉丁语1母语0"
            "法律5图书馆20图书馆使用20聆听20开锁1撬锁1锁匠1机械维修10医学1博物学10"
            "自然学10领航10导航10神秘学5重型操作1重型机械1操作重型机械1重型1说服10"
            "精神分析1心理学10骑术5妙手10侦查25潜行20生存10游泳20投掷20追踪10驯兽5"
            "潜水1爆破1读唇1催眠1炮术1"
        )

        matches = re.findall(r"([\u4e00-\u9fa5a-zA-Z]+)(\d+)", attributes)
        initial_matches = re.findall(r"([\u4e00-\u9fa5a-zA-Z]+)(\d+)", initial_data)
        attributes_dict = {attr: int(value) for attr, value in initial_matches}
        for attr, val in matches:
            attributes_dict[attr] = int(val)

        attributes_dict['max_hp'] = (attributes_dict.get('siz', 0) + attributes_dict.get('con', 0)) // 10
        attributes_dict['max_san'] = attributes_dict.get('pow', 0)

        chara_id = charmod.create_character(user_id, name, attributes_dict)
        response = get_output("pc.create.success", name=name, id=chara_id)

        yield event.plain_result(response)
        await self.save_log(group_id=event.get_group_id(), content=response)

    @pc.command("show")
    async def pc_show_character(self, event, attribute_name: Optional[str] = None):
        user_id = event.get_sender_id()
        chara_id = charmod.get_current_character_id(user_id)

        if not chara_id:
            yield event.plain_result(get_output("pc.show.no_active"))
            return

        chara_data = charmod.load_character(user_id, chara_id)
        if not chara_data:
            yield event.plain_result(get_output("pc.show.load_fail", id=chara_id))
            return

        if attribute_name:
            if attribute_name not in chara_data["attributes"]:
                yield event.plain_result(get_output("pc.show.attr_missing", attribute=attribute_name))
                return
            val = chara_data["attributes"][attribute_name]
            yield event.plain_result(get_output("pc.show.attr", attr=attribute_name, value=val))
        else:
            attributes = "\n".join([f"{key}: {value}" for key, value in chara_data["attributes"].items()])
            yield event.plain_result(get_output("pc.show.all", name=chara_data['name'], attributes=attributes))

    @pc.command("list")
    async def pc_list_characters(self, event):
        user_id = event.get_sender_id()
        characters = charmod.get_all_characters(user_id)
        if not characters:
            yield event.plain_result(get_output("pc.list.empty"))
            return

        current = charmod.get_current_character_id(user_id)
        chara_list = "\n".join([f"- {name} (ID: {ch}) {'(当前)' if ch == current else ''}" for name, ch in characters.items()])
        yield event.plain_result(get_output("pc.list.result", list=chara_list))

    @pc.command("change")
    async def pc_change_character(self, event, name: str):
        user_id = event.get_sender_id()
        characters = charmod.get_all_characters(user_id)
        if name not in characters:
            yield event.plain_result(get_output("pc.change.missing", name=name))
            return

        charmod.set_current_character(user_id, characters[name])
        yield event.plain_result(get_output("pc.change.success", name=name))

    @pc.command("update")
    async def pc_update_character(self, event, attribute: str, value: str):
        user_id = event.get_sender_id()
        chara_id = charmod.get_current_character_id(user_id)
        if not chara_id:
            yield event.plain_result(get_output("pc.update.no_active"))
            return

        match = re.match(r"([+\-*]?)(\d*)([dD]?)(\d*)", value)
        if not match:
            yield event.plain_result(get_output("pc.update.error_format"))
            return

        operator = match.group(1) or None
        expr = match.group(2) + match.group(3) + match.group(4)

        value_num, roll_detail = _parse_dice_expr(expr)
        if value_num is None:
            yield event.plain_result(get_output("pc.update.error_format"))
            return

        text, error = await self._apply_attribute_change(event, user_id, chara_id, attribute, operator, value_num, roll_detail)
        if error:
            yield event.plain_result(error)
            return

        yield event.plain_result(text)

    @pc.command("delete")
    async def pc_delete_character(self, event, name: str):
        user_id = event.get_sender_id()
        success, _ = charmod.delete_character(user_id, name)
        if not success:
            yield event.plain_result(get_output("pc.delete.fail", name=name))
            return
        yield event.plain_result(get_output("pc.delete.success", name=name))

    @filter.command("sn")
    async def filter_set_nickname(self, event):
        if event.get_platform_name() != "aiocqhttp":
            yield event.plain_result(get_output("nick.platform_unsupported"))
            return

        client = event.bot
        user_id = event.get_sender_id()
        group_id = event.get_group_id()

        chara_id = charmod.get_current_character_id(user_id)
        chara_data = charmod.load_character(user_id, chara_id)
        if not chara_data:
            yield event.plain_result(get_output("nick.no_character", id=chara_id))
            return

        max_hp = (chara_data['attributes'].get('con', 0) + chara_data['attributes'].get('siz', 0)) // 10
        name = chara_data['name']
        hp = chara_data['attributes'].get('hp', 0)
        san = chara_data['attributes'].get('san', 0)
        dex = chara_data['attributes'].get('dex', 0)
        new_card = f"{name} HP:{hp}/{max_hp} SAN:{san} DEX:{dex}"

        payloads = {"group_id": group_id, "user_id": user_id, "card": new_card}
        await client.api.call_action("set_group_card", **payloads)

        yield event.plain_result(get_output("nick.success"))
