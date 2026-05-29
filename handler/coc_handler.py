from astrbot.api.event import AstrMessageEvent

from ..component import character as charmod
from ..component import dice as dice_mod
from ..component import sanity
from ..component.output import get_output
from ..component.utils import get_sender_nickname


class CoCMixin:

    async def roll_attribute(self, event: AstrMessageEvent, skill_name: str, skill_value: str = None):
        user_id = event.get_sender_id()
        group_id = event.get_group_id()

        if skill_value is None:
            skill_value = charmod.get_skill_value(user_id, skill_name)

        client = event.bot
        ret = await get_sender_nickname(client, group_id, user_id)
        ret = event.get_sender_name() if ret == "" else ret
        result_message = dice_mod.roll_attribute(skill_name, skill_value, str(group_id), ret)
        result_message = await self._beautify(result_message, event)
        await self._reply_to_group(event, result_message)

    async def roll_attribute_penalty(self, event: AstrMessageEvent, dice_count: str = "1", skill_name: str = "", skill_value: str = None):
        user_id = event.get_sender_id()
        group_id = event.get_group_id()

        if skill_value is None:
            skill_value = charmod.get_skill_value(user_id, skill_name)

        client = event.bot
        ret = await get_sender_nickname(client, group_id, user_id)
        ret = event.get_sender_name() if ret == "" else ret
        result_message = dice_mod.roll_attribute_penalty(dice_count, skill_name, skill_value, str(group_id), ret)
        result_message = await self._beautify(result_message, event)
        await self._reply_to_group(event, result_message)

    async def roll_attribute_bonus(self, event: AstrMessageEvent, dice_count: str = "1", skill_name: str = "", skill_value: str = None):
        user_id = event.get_sender_id()
        group_id = event.get_group_id()

        if skill_value is None:
            skill_value = charmod.get_skill_value(user_id, skill_name)

        client = event.bot
        ret = await get_sender_nickname(client, group_id, user_id)
        ret = event.get_sender_name() if ret == "" else ret
        result_message = dice_mod.roll_attribute_bonus(dice_count, skill_name, skill_value, str(group_id), ret)
        result_message = await self._beautify(result_message, event)
        await self._reply_to_group(event, result_message)

    async def pc_grow_up(self, event: AstrMessageEvent, skill_name: str, skill_value: str = None):
        user_id = event.get_sender_id()

        result_str = charmod.grow_up(user_id, skill_name=skill_name, skill_value=skill_value)
        result_str = await self._beautify(result_str, event)
        await self._reply_to_group(event, result_str)

    async def pc_san_check(self, event: AstrMessageEvent, loss_formula: str):
        user_id = event.get_sender_id()
        chara_data = charmod.get_current_character(user_id)

        if not chara_data:
            yield event.plain_result(get_output("pc.show.no_active"))
            return

        roll_result, san_value, result_msg, loss, new_san = sanity.san_check(chara_data, loss_formula)

        chara_data["attributes"]["san"] = new_san
        charmod.save_character(user_id, chara_data["id"], chara_data)

        text = sanity.format_san_result(chara_data, roll_result, san_value, result_msg, loss, new_san)
        text = await self._beautify(text, event)
        await self._reply_to_group(event, text)

    async def pc_temporary_insanity(self, event: AstrMessageEvent):
        result = sanity.get_temporary_insanity(sanity.phobias, sanity.manias)
        text = get_output("san.temporary_insanity", result=result)
        text = await self._beautify(text, event)
        await self.save_log(group_id=event.get_group_id(), content=text)
        yield event.plain_result(text)

    async def pc_long_term_insanity(self, event: AstrMessageEvent):
        result = sanity.get_long_term_insanity(sanity.phobias, sanity.manias)
        text = get_output("san.long_term_insanity", result=result)
        text = await self._beautify(text, event)
        await self.save_log(group_id=event.get_group_id(), content=text)
        yield event.plain_result(text)
