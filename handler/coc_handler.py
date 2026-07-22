"""
COC 相关命令处理 Mixin（技能检定、理智检定、疯狂症状、技能成长）。

注意：@filter.command 装饰器不会被 AstrBot 调度（原因同 dice_handler.py），
实际命令路由见 handler/router.py。
"""

from ..component.astrbot_compat import filter, AstrMessageEvent

from ..component import character as charmod
from ..component import dice as dice_mod
from ..component import sanity
from ..component.output import get_output
from ..component.platform_adapter import get_adapter


class CoCMixin:

    @filter.command("ra")
    async def roll_attribute(self, event: AstrMessageEvent, skill_name: str = "", skill_value: str = None) -> str:
        user_id = event.get_sender_id()
        group_id = event.get_group_id()

        if skill_value is None:
            skill_value = charmod.get_skill_value(user_id, skill_name)

        adapter = get_adapter(event)
        name = await adapter.get_nickname(event)
        result_message = dice_mod.roll_attribute(skill_name, skill_value, str(group_id), name)
        result_message = await self._beautify(result_message, event)
        await self.save_log(group_id=event.get_group_id(), content=result_message)

        return result_message

    # 惩罚骰技能判定
    @filter.command("rap")
    async def cmd_rap(self, event: AstrMessageEvent, arg1: str = "", arg2: str = "", arg3: str = ""):
        """惩罚骰技能判定 (.rap 1 侦查 50 或 .rap 侦查 50)"""
        if arg1.isdigit():
            dice_count = arg1
            skill_name = arg2
            skill_value = arg3 if arg3 else None
        else:
            dice_count = "1"
            skill_name = arg1
            skill_value = arg2 if arg2 else None
        await self.roll_attribute_penalty(event, dice_count, skill_name, skill_value)

    async def roll_attribute_penalty(self, event: AstrMessageEvent, dice_count: str = "1", skill_name: str = "", skill_value: str = None) -> str:
        user_id = event.get_sender_id()
        group_id = event.get_group_id()

        if skill_value is None:
            skill_value = charmod.get_skill_value(user_id, skill_name)

        adapter = get_adapter(event)
        name = await adapter.get_nickname(event)
        result_message = dice_mod.roll_attribute_penalty(dice_count, skill_name, skill_value, str(group_id), name)
        result_message = await self._beautify(result_message, event)
        await self.save_log(group_id=event.get_group_id(), content=result_message)

        return result_message

    # 奖励骰技能判定
    @filter.command("rab")
    async def cmd_rab(self, event: AstrMessageEvent, arg1: str = "", arg2: str = "", arg3: str = ""):
        """奖励骰技能判定 (.rab 1 侦查 50 或 .rab 侦查 50)"""
        if arg1.isdigit():
            dice_count = arg1
            skill_name = arg2
            skill_value = arg3 if arg3 else None
        else:
            dice_count = "1"
            skill_name = arg1
            skill_value = arg2 if arg2 else None
        await self.roll_attribute_bonus(event, dice_count, skill_name, skill_value)

    async def roll_attribute_bonus(self, event: AstrMessageEvent, dice_count: str = "1", skill_name: str = "", skill_value: str = None) -> str:
        user_id = event.get_sender_id()
        group_id = event.get_group_id()

        if skill_value is None:
            skill_value = charmod.get_skill_value(user_id, skill_name)

        adapter = get_adapter(event)
        name = await adapter.get_nickname(event)
        result_message = dice_mod.roll_attribute_bonus(dice_count, skill_name, skill_value, str(group_id), name)
        result_message = await self._beautify(result_message, event)
        await self.save_log(group_id=event.get_group_id(), content=result_message)

        return result_message

    @filter.command("en")
    async def cmd_en(self, event: AstrMessageEvent, skill_name: str = "", skill_value: str = ""):
        """技能成长判定 (.en 侦查 50)"""
        skill_value = skill_value if skill_value else None
        text = await self.pc_grow_up(event, skill_name, skill_value)
        yield event.plain_result(text)

    async def pc_grow_up(self, event: AstrMessageEvent, skill_name: str, skill_value: str = None) -> str:
        """
        .en 技能成长判定
        调用 character 模块的 grow_up 生成结果文本，交给调用方发送。
        """
        user_id = event.get_sender_id()

        result_str = charmod.grow_up(user_id, skill_name=skill_name, skill_value=skill_value)
        result_str = await self._beautify(result_str, event)
        await self.save_log(group_id=event.get_group_id(), content=result_str)

        return result_str

    # san check
    @filter.command("sc")
    async def cmd_sc(self, event: AstrMessageEvent, loss_formula: str = "1d6/1d10"):
        """理智检定"""
        async for result in self.pc_san_check(event, loss_formula):
            yield result

    async def pc_san_check(self, event: AstrMessageEvent, loss_formula: str):
        """理智检定"""
        user_id = event.get_sender_id()
        chara_data = charmod.get_current_character(user_id)

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
        await self.save_log(group_id=event.get_group_id(), content=text)

        adapter = get_adapter(event)
        sent = await adapter.send_group_message(event, text, reply=True)
        if not sent:
            yield event.plain_result(text)

    @filter.command("ti")
    async def pc_temporary_insanity(self, event: AstrMessageEvent):
        """临时疯狂"""
        result = sanity.get_temporary_insanity(sanity.phobias, sanity.manias)
        text = get_output("san.temporary_insanity", result=result)
        text = await self._beautify(text, event)
        await self.save_log(group_id=event.get_group_id(), content=text)
        yield event.plain_result(text)

    @filter.command("li")
    async def pc_long_term_insanity(self, event: AstrMessageEvent):
        """长期疯狂"""
        result = sanity.get_long_term_insanity(sanity.phobias, sanity.manias)
        text = get_output("san.long_term_insanity", result=result)
        text = await self._beautify(text, event)
        await self.save_log(group_id=event.get_group_id(), content=text)
        yield event.plain_result(text)
