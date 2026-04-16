import time

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.all import *
from astrbot.api import AstrBotConfig

from .component import dice as dice_mod
from .component.output import get_output, get_config, set_config
from .component.utils import roll_character, format_character, roll_dnd_character, format_dnd_character
from .component.rules import modify_coc_great_sf_rule_command
from .component.log import JSONLoggerCore

from .handler import (
    DiceMixin,
    CharacterMixin,
    CoCMixin,
    InitiativeMixin,
    LogMixin,
    LLMToolsMixin,
    RouterMixin,
)

logger_core = JSONLoggerCore()

async def init():
    await logger_core.initialize()

_LLM_DEFAULT_SYSTEM_PROMPT = (
    "你是一个跑团骰娘，风格活泼可爱。"
    "请用简短生动的语言（不超过60字）描述以下掷骰结果，"
    "可以加入一点点角色扮演风格，但必须保留所有数字和判定结论。"
)


@register("astrbot_plugin_trpgdice_rerolled", "星空凌", "TRPG玩家用骰", "1.2.0")
class DicePlugin(
    DiceMixin,
    CharacterMixin,
    CoCMixin,
    InitiativeMixin,
    LogMixin,
    LLMToolsMixin,
    RouterMixin,
    Star,
):
    def __init__(self, context: Context, config: AstrBotConfig):
        self.wakeup_prefix = [".", "。", "/"]
        self.logger_core = logger_core
        # 初始化配置系统
        set_config(config)

        super().__init__(context)

    async def save_log(self, group_id, content):
        await self.logger_core.add_message(
            group_id=group_id,
            user_id="Bot",
            nickname="风铃Velinithra",
            timestamp=int(time.time()),
            text=content,
            isDice=True
        )

    async def _beautify(self, raw_text: str, event: AstrMessageEvent) -> str:
        """若 LLM 模式已启用，将原始结果文本交给 LLM 美化后返回；否则原样返回。"""
        if not get_config("llm_mode.enabled", False):
            return raw_text
        try:
            prov = self.context.get_using_provider(umo=event.unified_msg_origin)
            if not prov:
                return raw_text
            system_prompt = get_config("llm_mode.system_prompt", _LLM_DEFAULT_SYSTEM_PROMPT) or _LLM_DEFAULT_SYSTEM_PROMPT
            model = get_config("llm_mode.model", "") or None
            resp = await prov.text_chat(
                prompt=raw_text,
                context=[],
                system_prompt=system_prompt,
                model=model
            )
            return resp.completion_text or raw_text
        except Exception:
            return raw_text

    # ======================== 杂项命令 ============================= #

    @filter.command("coc")
    async def generate_coc_character(self, event: AstrMessageEvent, x: int = 1):
        characters = [roll_character() for _ in range(x)]
        results = []
        for i, char in enumerate(characters):
            results.append(format_character(char, index=i+1))
        text = get_output("character_list.coc", characters="\n\n".join(results))
        text = await self._beautify(text, event)
        yield event.plain_result(text)

    @filter.command("dnd")
    async def generate_dnd_character(self, event: AstrMessageEvent, x: int = 1):
        characters = [roll_dnd_character() for _ in range(x)]
        results = []
        for i, char in enumerate(characters):
            results.append(format_dnd_character(char, index=i+1))
        text = get_output("character_list.dnd", characters="\n\n".join(results))
        text = await self._beautify(text, event)
        yield event.plain_result(text)

    @filter.command("dicehelp")
    async def help(self, event: AstrMessageEvent):
        help_text = (
            "基础掷骰\n"
            "`/r 1d100` - 掷 1 个 100 面骰\n"
            "`/r 3d6+2d4-1d8` - 掷 3 个 6 面骰 + 2 个 4 面骰 - 1 个 8 面骰\n"
            "`/r 3#1d20` - 掷 1d20 骰 3 次\n"
            "`/r 10d6k5` - 掷 10 个 6 面骰，保留最高 5 个\n\n"

            "人物卡管理\n"
            "`/pc create 名称 属性值` - 创建人物卡\n"
            "`/pc show` - 显示当前人物卡\n"
            "`/pc list` - 列出所有人物卡\n"
            "`/pc change 名称` - 切换当前人物卡\n"
            "`/pc update 属性 值/公式` - 更新人物卡属性\n"
            "`/pc delete 名称` - 删除人物卡\n\n"

            "CoC 相关\n"
            "`/coc x` - 生成 x 个 CoC 角色数据\n"
            "`/ra 技能名` - 进行技能骰\n"
            "`/rap n 技能名` - 带 n 个惩罚骰的技能骰\n"
            "`/rab n 技能名` - 带 n 个奖励骰的技能骰\n"
            "`/sc 1d6/1d10` - 进行 San Check\n"
            "`/ti` - 生成临时疯狂症状\n"
            "`/li` - 生成长期疯狂症状\n"
            "`/en 技能名 [技能值]` - 技能成长\n"
            "`/setcoc 规则编号` - 设置COC规则\n\n"

            "DnD 相关\n"
            "`/dnd x` - 生成 x 个 DnD 角色属性\n"
            "`/init` - 显示当前先攻列表\n"
            "`/init clr` - 清空先攻列表\n"
            "`/init del [角色名]` - 删除角色先攻（默认为用户名）\n"
            "`/ri +/- x` - 以x的调整值投掷先攻\n"
            "`/ri x [角色名]` - 将角色（默认为用户名）的先攻设置为x\n"
            "`/ed` - 结束当前回合\n"
            "`/fireball n` - 施放 n 环火球术，计算伤害\n\n"

            "其他规则\n"
            "`/rv 骰子数量 难度` - 进行吸血鬼规则掷骰判定\n\n"

            "Log 管理\n"
            "`/log new <日志名>` - 开始新的日志会话\n"
            "`/log off` - 暂停当前的日志会话\n"
            "`/log on` - 开始当前的日志会话\n"
            "`/log end` - 结束当前的日志会话\n"
            "`/log del <日志名>` - 删除日志会话\n"
            "`/log get <日志名>` - 获取日志会话\n"
            "`/log stat <日志名>` - 获取日志会话统计信息\n"
        )

        yield event.plain_result(help_text)

    @filter.command("fireball")
    async def fireball_cmd(self, event: AstrMessageEvent, ring: int = 3):
        ring = max(3, min(ring, 20))
        result = dice_mod.fireball(ring)
        result = await self._beautify(result, event)
        yield event.plain_result(result)

    @filter.command("jrrp")
    async def roll_RP_cmd(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        result = dice_mod.roll_RP(user_id)
        result = await self._beautify(result, event)
        yield event.plain_result(result)

    @filter.command("setcoc")
    async def setcoc_cmd(self, event: AstrMessageEvent, command: str = " "):
        group_id = event.get_group_id()
        result = modify_coc_great_sf_rule_command(group_id, command)
        yield event.plain_result(result)
