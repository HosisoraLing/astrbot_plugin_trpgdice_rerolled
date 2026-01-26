import random
import re
import os
import json

from .output import get_output, get_config, _config

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

# 恐惧
with open(PLUGIN_DIR + "/../data/phobias.json", "r", encoding="utf-8") as f:
    phobias = json.load(f)["phobias"]

# 躁狂
with open(PLUGIN_DIR + "/../data/mania.json", "r", encoding="utf-8") as f:
    manias = json.load(f)["manias"]

# 从配置文件中获取疯狂症状类型
def get_insanity_types(key: str):
    """从配置文件中获取疯狂症状类型列表"""
    config = _config.get("output", {}).get("san", {})
    types = config.get(key, [])
    if not types:
        # 如果配置中没有，返回空列表
        return []
    return types

def parse_san_loss_formula(formula: str):
    """
    解析 SAN 损失公式，返回成功和失败时的损失表达式。
    例如 "1d6/1d10" -> ("1d6", "1d10")
    """
    parts = formula.split("/")
    success_part = parts[0]
    failure_part = parts[1] if len(parts) > 1 else parts[0]
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
    """
    进行一次理智检定，返回检定结果和损失值。
    chara_data: 当前人物卡数据（需包含'san'属性）
    loss_formula: 损失公式，如 "1d6/1d10"
    返回：(roll_result, san_value, result_msg, loss, new_san)
    """
    san_value = chara_data["attributes"].get("san", 0)
    dice_min = get_config("sanity.dice_range.min", 1)
    dice_max = get_config("sanity.dice_range.max", 100)
    roll_result = random.randint(dice_min, dice_max)
    success_loss, failure_loss = parse_san_loss_formula(loss_formula)

    if roll_result <= san_value:
        loss = roll_loss(success_loss)
        result_msg = get_output("san.check.success")
    else:
        loss = roll_loss(failure_loss)
        result_msg = get_output("san.check.failure")

    new_san = max(0, san_value - loss)
    return roll_result, san_value, result_msg, loss, new_san

def get_temporary_insanity(phobias: dict, manias: dict):
    """
    随机生成临时疯狂症状，返回症状文本。
    phobias, manias: 恐惧症和躁狂症字典
    """
    # 从配置文件中获取临时疯狂症状类型列表
    temporary_insanity_types = get_insanity_types("temporary_insanity_types")

    if not temporary_insanity_types:
        # 如果配置中没有，返回默认文本
        return "临时疯狂: 配置文件中未找到临时疯狂症状类型"

    # 从配置获取疯狂症状骰子配置
    insanity_dice = get_config("sanity.insanity_dice.dice", "1D10")
    insanity_min = get_config("sanity.insanity_dice.min", 1)
    insanity_max = get_config("sanity.insanity_dice.max", 10)
    phobia_mania_min = get_config("sanity.phobia_mania_range.min", 1)
    phobia_mania_max = get_config("sanity.phobia_mania_range.max", 100)

    # 随机选择一个症状
    roll = random.randint(1, len(temporary_insanity_types))
    result = temporary_insanity_types[roll - 1].replace(insanity_dice, str(random.randint(insanity_min, insanity_max)))

    if roll == 9:
        fear_roll = random.randint(phobia_mania_min, phobia_mania_max)
        result += f"\n→ 具体恐惧症：{phobias[str(fear_roll)]}（骰值 {fear_roll}）"
    if roll == 10:
        mania_roll = random.randint(phobia_mania_min, phobia_mania_max)
        result += f"\n→ 具体躁狂症：{manias[str(mania_roll)]}（骰值 {mania_roll}）"
    return result

def get_long_term_insanity(phobias: dict, manias: dict):
    """
    随机生成长期疯狂症状，返回症状文本。
    phobias, manias: 恐惧症和躁狂症字典
    """
    # 从配置文件中获取长期疯狂症状类型列表
    long_term_insanity_types = get_insanity_types("long_term_insanity_types")

    if not long_term_insanity_types:
        # 如果配置中没有，返回默认文本
        return "长期疯狂: 配置文件中未找到长期疯狂症状类型"

    # 从配置获取疯狂症状骰子配置
    insanity_dice = get_config("sanity.insanity_dice.dice", "1D10")
    insanity_min = get_config("sanity.insanity_dice.min", 1)
    insanity_max = get_config("sanity.insanity_dice.max", 10)
    phobia_mania_min = get_config("sanity.phobia_mania_range.min", 1)
    phobia_mania_max = get_config("sanity.phobia_mania_range.max", 100)

    # 随机选择一个症状
    roll = random.randint(1, len(long_term_insanity_types))
    result = long_term_insanity_types[roll - 1].replace(insanity_dice, str(random.randint(insanity_min, insanity_max)))

    if roll == 9:
        fear_roll = random.randint(phobia_mania_min, phobia_mania_max)
        result += f"\n→ 具体恐惧症：{phobias[str(fear_roll)]}（骰值 {fear_roll}）"
    if roll == 10:
        mania_roll = random.randint(phobia_mania_min, phobia_mania_max)
        result += f"\n→ 具体躁狂症：{manias[str(mania_roll)]}（骰值 {mania_roll}）"
    return result