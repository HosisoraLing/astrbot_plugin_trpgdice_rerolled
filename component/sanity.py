import random
import re
import os
import json

from .output import get_output, get_config, get_output_list

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

# 恐惧
with open(PLUGIN_DIR + "/../data/phobias.json", "r", encoding="utf-8") as f:
    phobias = json.load(f)["phobias"]

# 躁狂
with open(PLUGIN_DIR + "/../data/mania.json", "r", encoding="utf-8") as f:
    manias = json.load(f)["manias"]

def get_insanity_types(key: str):
    """从配置文件中获取疯狂症状类型列表"""
    return get_output_list(f"san.{key}", [])

def parse_san_loss_formula(formula: str):
    """
    解析 SAN 损失公式，返回成功和失败时的损失表达式。
    例如 "1d6/1d10" -> ("1d6", "1d10")
    合法格式：XdY 或 N，两部分以 / 分隔，各部分不超过 20 字符。
    """
    formula = formula.strip()[:50]  # 长度限制
    _LOSS_PART = re.compile(r"^\d{1,4}(?:[dD]\d{1,4})?$")
    parts = formula.split("/")
    success_part = parts[0].strip()
    failure_part = parts[1].strip() if len(parts) > 1 else success_part
    # 格式校验：每部分必须是纯数字或 XdY
    if not _LOSS_PART.match(success_part) or not _LOSS_PART.match(failure_part):
        return None, None   # 调用方检查 None 并报错
    return success_part, failure_part

def roll_loss(loss_expr: str):
    """
    根据损失表达式计算损失值。
    支持 "XdY" 或纯数字。
    """
    match = re.fullmatch(r"(\d+)[dD](\d+)", loss_expr)
    if match:
        num_dice, dice_size = map(int, match.groups())
        return sum(random.randint(1, dice_size) for _ in range(num_dice))
    elif loss_expr.isdigit():
        return int(loss_expr)
    return 0

def san_check(chara_data: dict, loss_formula: str):
    san_value = chara_data["attributes"].get("san", 0)
    dice_min = get_config("sanity.dice_range.min", 1)
    dice_max = get_config("sanity.dice_range.max", 100)
    roll_result = random.randint(dice_min, dice_max)
    success_loss, failure_loss = parse_san_loss_formula(loss_formula)
    if success_loss is None:
        return roll_result, san_value, get_output("san.check.failure"), 0, san_value

    if roll_result <= san_value:
        loss = roll_loss(success_loss)
        result_msg = get_output("san.check.success")
    else:
        loss = roll_loss(failure_loss)
        result_msg = get_output("san.check.failure")

    new_san = max(0, san_value - loss)
    return roll_result, san_value, result_msg, loss, new_san

def format_san_result(chara_data, roll_result, san_value, result_msg, loss, new_san):
    kwargs = dict(name=chara_data["name"], roll_result=roll_result,
                  san_value=san_value, result_msg=result_msg, loss=loss, new_san=new_san)
    if new_san == 0:
        return get_output("san.check_result.zero", **kwargs)
    if loss == 0:
        return get_output("san.check_result.no_loss", **kwargs)
    if loss < 5:
        return get_output("san.check_result.loss", **kwargs)
    return get_output("san.check_result.great_loss", **kwargs)

def _get_insanity(phobias, manias, kind):
    types = get_insanity_types(f"{kind}_insanity_types")
    if not types:
        return f"{'临时' if kind == 'temporary' else '长期'}疯狂: 配置文件中未找到症状类型"

    insanity_dice = get_config("sanity.insanity_dice.dice", "1D10")
    insanity_min = get_config("sanity.insanity_dice.min", 1)
    insanity_max = get_config("sanity.insanity_dice.max", 10)
    phobia_mania_min = get_config("sanity.phobia_mania_range.min", 1)
    phobia_mania_max = get_config("sanity.phobia_mania_range.max", 100)

    roll = random.randint(1, len(types))
    result = types[roll - 1].replace(insanity_dice, str(random.randint(insanity_min, insanity_max)))

    if roll == 9:
        fear_roll = random.randint(phobia_mania_min, phobia_mania_max)
        result += f"\n→ 具体恐惧症：{phobias[str(fear_roll)]}（骰值 {fear_roll}）"
    if roll == 10:
        mania_roll = random.randint(phobia_mania_min, phobia_mania_max)
        result += f"\n→ 具体躁狂症：{manias[str(mania_roll)]}（骰值 {mania_roll}）"
    return result

def get_temporary_insanity(phobias, manias):
    return _get_insanity(phobias, manias, "temporary")

def get_long_term_insanity(phobias, manias):
    return _get_insanity(phobias, manias, "long_term")