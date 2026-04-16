from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger

from ..component import character as charmod
from ..component import dice as dice_mod
from ..component import sanity
from ..component.output import get_output
from ..component.utils import get_sender_nickname


class CoCMixin:

    async def roll_attribute(self, event: AstrMessageEvent, skill_name: str, skill_value: str = None):
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        name = event.get_sender_name()

        if skill_value is None:
            skill_value = charmod.get_skill_value(user_id, skill_name)

        client = event.bot
        ret = await get_sender_nickname(client, group_id, user_id)

        logger.info(ret)

        ret = event.get_sender_name() if ret == "" else ret
        result_message = dice_mod.roll_attribute(skill_name, skill_value, str(group_id), ret)
        result_message = await self._beautify(result_message, event)
        payloads = {
            "group_id": group_id,
            "message": [
                {"type": "reply", "data": {"id": event.message_obj.message_id}},
                {"type": "at", "data": {"qq": user_id}},
                {"type": "text", "data": {"text": "\n" + result_message}}
            ]
        }
        await self.save_log(group_id=event.get_group_id(), content=result_message)
        await client.api.call_action("send_group_msg", **payloads)

    # 惩罚骰技能判定
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
        payloads = {
            "group_id": group_id,
            "message": [
                {"type": "reply", "data": {"id": event.message_obj.message_id}},
                {"type": "at", "data": {"qq": user_id}},
                {"type": "text", "data": {"text": "\n" + result_message}}
            ]
        }
        await self.save_log(group_id=event.get_group_id(), content=result_message)
        await client.api.call_action("send_group_msg", **payloads)

    # 奖励骰技能判定
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
        payloads = {
            "group_id": group_id,
            "message": [
                {"type": "reply", "data": {"id": event.message_obj.message_id}},
                {"type": "at", "data": {"qq": user_id}},
                {"type": "text", "data": {"text": "\n" + result_message}}
            ]
        }
        await self.save_log(group_id=event.get_group_id(), content=result_message)
        await client.api.call_action("send_group_msg", **payloads)

    # @filter.command("en")
    async def pc_grow_up(self, event: AstrMessageEvent, skill_name: str, skill_value: str = None):
        """
        .en 技能成长判定
        调用 character 模块的 grow_up 生成结果文本，再通过 event 发送给用户。
        """
        user_id = event.get_sender_id()

        result_str = charmod.grow_up(user_id, skill_name=skill_name, skill_value=skill_value)
        result_str = await self._beautify(result_str, event)
        group_id = event.get_group_id()
        client = event.bot
        payloads = {
            "group_id": group_id,
            "message": [
                {"type": "reply", "data": {"id": event.message_obj.message_id}},
                {"type": "at", "data": {"qq": user_id}},
                {"type": "text", "data": {"text": "\n" + result_str}}
            ]
        }
        await self.save_log(group_id=event.get_group_id(), content=result_str)
        await client.api.call_action("send_group_msg", **payloads)

    # san check
    # @filter.command("sc")
    async def pc_san_check(self, event: AstrMessageEvent, loss_formula: str):
        """理智检定"""
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        chara_data = charmod.get_current_character(user_id)
        client = event.bot

        if not chara_data:
            yield event.plain_result(get_output("pc.show.no_active"))
            return

        roll_result, san_value, result_msg, loss, new_san = sanity.san_check(chara_data, loss_formula)

        # 更新人物卡
        chara_data["attributes"]["san"] = new_san
        charmod.save_character(user_id, chara_data["id"], chara_data)

        if new_san == 0:
            text = get_output(
                    "san.check_result.zero",
                    name=chara_data["name"],
                    roll_result=roll_result,
                    san_value=san_value,
                    result_msg=result_msg,
                    loss=loss,
                    new_san=new_san
                )

        elif loss == 0:
            text = get_output(
                "san.check_result.no_loss",
                name=chara_data["name"],
                roll_result=roll_result,
                san_value=san_value,
                result_msg=result_msg,
                loss=loss,
                new_san=new_san
            )
        elif loss < 5:
            text = get_output(
                "san.check_result.loss",
                name=chara_data["name"],
                roll_result=roll_result,
                san_value=san_value,
                result_msg=result_msg,
                loss=loss,
                new_san=new_san
            )
        else:
            text = get_output(
                "san.check_result.great_loss",
                name=chara_data["name"],
                roll_result=roll_result,
                san_value=san_value,
                result_msg=result_msg,
                loss=loss,
                new_san=new_san
            )

        text = await self._beautify(text, event)
        payloads = {
            "group_id": group_id,
            "message": [
                {"type": "reply", "data": {"id": event.message_obj.message_id}},
                {"type": "at", "data": {"qq": user_id}},
                {"type": "text", "data": {"text": "\n" + text}}
            ]
        }
        await self.save_log(group_id=event.get_group_id(), content=text)
        await client.api.call_action("send_group_msg", **payloads)

    async def pc_temporary_insanity(self, event: AstrMessageEvent):
        """临时疯狂"""
        result = sanity.get_temporary_insanity(sanity.phobias, sanity.manias)
        text = get_output("san.temporary_insanity", result=result)
        text = await self._beautify(text, event)
        await self.save_log(group_id=event.get_group_id(), content=text)
        yield event.plain_result(text)

    async def pc_long_term_insanity(self, event: AstrMessageEvent):
        """长期疯狂"""
        result = sanity.get_long_term_insanity(sanity.phobias, sanity.manias)
        text = get_output("san.long_term_insanity", result=result)
        text = await self._beautify(text, event)
        await self.save_log(group_id=event.get_group_id(), content=text)
        yield event.plain_result(text)
