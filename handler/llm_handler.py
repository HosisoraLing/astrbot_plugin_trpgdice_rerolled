import re
from typing import Optional

from astrbot.api.event import filter, AstrMessageEvent

from ..component import character as charmod
from ..component import dice as dice_mod
from ..component import sanity
from ..component.output import get_output
from ..component.utils import roll_character, format_character, roll_dnd_character, format_dnd_character


class LLMToolsMixin:

    @filter.llm_tool(name="roll_dice")
    async def llm_tool_roll_dice(self, event: AstrMessageEvent, expression: str = "1d100") -> Optional[str]:
        """为玩家掷骰子，支持各种骰子表达式。

        Args:
            expression(string): 骰子表达式，例如 1d100、3d6、2d6+5、10d6k5（保留最高5个）、3#1d20（掷3次）
        """
        expression = expression.strip()[:200]
        return dice_mod.handle_roll_dice(expression, name=event.get_sender_name())

    @filter.llm_tool(name="skill_check")
    async def llm_tool_skill_check(self, event: AstrMessageEvent, skill_name: str, skill_value: int) -> Optional[str]:
        """进行 COC 技能检定，掷 1d100 与技能值比较，判断成功/失败等级。

        Args:
            skill_name(string): 技能名称，例如 侦查、射击、格斗
            skill_value(number): 技能当前值（0-100）
        """
        skill_name = skill_name.strip()[:30]
        skill_value = max(0, min(int(skill_value), 100))
        group_id = str(event.get_group_id() or "0")
        name = event.get_sender_name()
        return dice_mod.roll_attribute(skill_name, skill_value, group_id, name)

    @filter.llm_tool(name="san_check")
    async def llm_tool_san_check(self, event: AstrMessageEvent, loss_formula: str = "1d6/1d10") -> Optional[str]:
        """对当前人物卡进行理智检定（SAN Check），自动更新理智值。

        Args:
            loss_formula(string): 理智损失公式，格式为 成功损失/失败损失，例如 1d3/1d6、0/1d8
        """
        user_id = event.get_sender_id()
        chara_data = charmod.get_current_character(user_id)
        if not chara_data:
            return get_output("pc.show.no_active")
        roll_result, san_value, result_msg, loss, new_san = sanity.san_check(chara_data, loss_formula)
        chara_data["attributes"]["san"] = new_san
        charmod.save_character(user_id, chara_data["id"], chara_data)
        if new_san == 0:
            return get_output("san.check_result.zero", name=chara_data["name"], roll_result=roll_result, san_value=san_value, result_msg=result_msg, loss=loss, new_san=new_san)
        if loss == 0:
            return get_output("san.check_result.no_loss", name=chara_data["name"], roll_result=roll_result, san_value=san_value, result_msg=result_msg, loss=loss, new_san=new_san)
        if loss < 5:
            return get_output("san.check_result.loss", name=chara_data["name"], roll_result=roll_result, san_value=san_value, result_msg=result_msg, loss=loss, new_san=new_san)
        return get_output("san.check_result.great_loss", name=chara_data["name"], roll_result=roll_result, san_value=san_value, result_msg=result_msg, loss=loss, new_san=new_san)

    @filter.llm_tool(name="roll_coc_character")
    async def llm_tool_roll_coc_character(self, event: AstrMessageEvent, count: int = 1) -> Optional[str]:
        """生成 COC 克苏鲁调查员属性，包含力量、体质、体型、敏捷等基础属性。

        Args:
            count(number): 生成角色数量，默认1，最多5
        """
        count = max(1, min(count, 5))
        chars = [roll_character() for _ in range(count)]
        results = [format_character(c, index=i + 1) for i, c in enumerate(chars)]
        return "\n\n".join(results)

    @filter.llm_tool(name="roll_dnd_character")
    async def llm_tool_roll_dnd_character(self, event: AstrMessageEvent, count: int = 1) -> Optional[str]:
        """生成 D&D 冒险者的六项基础属性（4d6去最低）。

        Args:
            count(number): 生成角色数量，默认1，最多5
        """
        count = max(1, min(count, 5))
        chars = [roll_dnd_character() for _ in range(count)]
        results = [format_dnd_character(c, index=i + 1) for i, c in enumerate(chars)]
        return "\n\n".join(results)

    @filter.llm_tool(name="fireball_damage")
    async def llm_tool_fireball(self, event: AstrMessageEvent, ring: int = 3) -> Optional[str]:
        """计算 D&D 火球术伤害，基础3环为8d6，每升一环加1d6。

        Args:
            ring(number): 法术环位，最低3，例如 3、5、9
        """
        return dice_mod.fireball(ring)

    @filter.llm_tool(name="daily_luck")
    async def llm_tool_daily_luck(self, event: AstrMessageEvent) -> Optional[str]:
        """查询今日运势（JRRP），结果基于用户ID和日期生成，每日固定。"""
        return dice_mod.roll_RP(event.get_sender_id())

    @filter.llm_tool(name="set_output_template")
    async def llm_tool_set_output_template(self, event: AstrMessageEvent, template_key: str, template_value: str) -> Optional[str]:
        """修改骰子插件的输出模板，让输出更符合跑团风格。模板中可以使用 {变量名} 作为占位符。

        Args:
            template_key(string): 模板路径，例如 dice.normal.success、skill_check.normal、san.check_result.loss
            template_value(string): 新的模板内容，使用 {变量名} 占位符，例如 {name} 掷出了 {result}，总计 {total} 点！
        """
        # key：只允许字母/数字/点，防止注入奇怪路径
        if not re.match(r'^[a-zA-Z0-9_.]{1,80}$', template_key):
            return "模板路径格式无效，仅允许字母、数字和点。"
        # value：限制长度，防止过大
        template_value = template_value[:500]
        # 占位符安全检查：确保花括号已正确配对
        open_braces = template_value.count('{')
        close_braces = template_value.count('}')
        if open_braces != close_braces:
            return "模板格式无效，花括号未正确配对（开括号数与闭括号数不等）。"
        from ..component.output import set_output_override
        _, msg = set_output_override(template_key, template_value)
        return msg

    @filter.llm_tool(name="set_llm_mode")
    async def llm_tool_set_llm_mode(self, event: AstrMessageEvent, enabled: bool, system_prompt: str = "") -> Optional[str]:
        """开启或关闭 LLM 美化模式，并可选择设置美化提示词。

        Args:
            enabled(boolean): 是否启用 LLM 美化模式
            system_prompt(string): LLM 美化时使用的系统提示词，留空则使用默认提示词
        """
        if system_prompt and len(system_prompt) > 2000:
            return "系统提示词过长，请控制在 2000 字以内。"
        from ..component.output import set_config_override
        set_config_override("llm_mode.enabled", enabled)
        if system_prompt:
            set_config_override("llm_mode.system_prompt", system_prompt)
        status = "已开启" if enabled else "已关闭"
        return f"LLM 美化模式{status}。" + (" 提示词已更新。" if system_prompt else "")
