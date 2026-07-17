import random
import re
import datetime
import hashlib

from .output import get_output, get_config
from .rules import great_success_range, great_failure_range, get_great_sf_rule, set_great_sf_rule, GREAT_SF_RULE_DEFAULT, GREAT_SF_RULE_STR


def roll_dice(dice_count, dice_faces):
    """掷 `dice_count` 个 `dice_faces` 面骰"""
    return [random.randint(1, dice_faces) for _ in range(dice_count)]


def roll_coc_bonus_penalty(base_roll, bonus_dice=0, penalty_dice=0):
    """奖励骰 / 惩罚骰"""
    tens_digit = base_roll // 10
    ones_digit = base_roll % 10
    if ones_digit == 0:
        ones_digit = 10

    alternatives = []
    for _ in range(max(bonus_dice, penalty_dice)):
        new_tens = random.randint(0, 9)
        alternatives.append(new_tens * 10 + ones_digit)

    if bonus_dice > 0:
        return min([base_roll] + alternatives)
    elif penalty_dice > 0:
        return max([base_roll] + alternatives)
    return base_roll


def parse_dice_expression(expression):
    """
    解析骰子表达式，并格式化输出。
    支持普通骰、奖励/惩罚骰。
    返回 (总和, 格式化字符串, 是否连续掷骰)
    """
    expression = expression.replace("x", "*").replace("X", "*").strip()

    if len(expression) > 200:
        return None, get_output("dice.format_error", expr=expression[:20] + "..."), False

    max_count = get_config("dice.max_count", 100)
    max_faces = get_config("dice.max_faces", 1000)
    max_repeat = get_config("dice.max_repeat", 20)

    match_repeat = re.match(r"(\d+)?#(.+)", expression)
    roll_times = 1
    bonus_dice = 0
    penalty_dice = 0

    if match_repeat:
        roll_times = int(match_repeat.group(1)) if match_repeat.group(1) else 1
        if roll_times > max_repeat:
            return None, get_output("dice.repeat_limit_error", max_repeat=max_repeat), False
        expression = match_repeat.group(2)

        if expression in ["p", "b"]:
            penalty_dice = 1 if expression == "p" else 0
            bonus_dice = 1 if expression == "b" else 0
            bonus_penalty_dice_count = get_config("dice.bonus_penalty.dice_count", 1)
            bonus_penalty_base_faces = get_config("dice.bonus_penalty.base_faces", 100)
            expression = f"{bonus_penalty_dice_count}d{bonus_penalty_base_faces}"

    results = []
    total = None
    is_multi_roll = roll_times > 1

    for _ in range(roll_times):
        parts = re.split(r"([+\-*])", expression)
        subtotal = None
        formatted_parts = []
        roll_total = None

        for i in range(0, len(parts), 2):
            expr = parts[i].strip()
            operator = parts[i - 1] if i > 0 else "+"

            if expr.isdigit():
                subtotal = int(expr)
                roll_result = f"{subtotal}"
            else:
                match = re.match(r"(\d*)[dD](\d+)([kK]\d+)?([+\-*]\d+)?", expr)
                if not match:
                    return None, get_output("dice.format_error", expr=expr), False

                dice_count = int(match.group(1)) if match.group(1) else 1
                dice_faces = int(match.group(2))
                raw_keep = int(match.group(3)[1:]) if match.group(3) else None
                modifier = match.group(4)

                if not (1 <= dice_count <= max_count and 1 <= dice_faces <= max_faces):
                    return None, get_output("dice.limit_error"), False

                if raw_keep is not None:
                    if not (1 <= raw_keep <= dice_count):
                        return None, get_output("dice.keep_error", keep=raw_keep, dice_count=dice_count), False
                    keep_highest = raw_keep
                else:
                    keep_highest = dice_count

                # COC 奖励/惩罚骰
                if dice_count == 1 and dice_faces == 100 and (bonus_dice > 0 or penalty_dice > 0):
                    base_tens = random.randint(0, 9)
                    unit = random.randint(0, 9)
                    rolls = [random.randint(0, 9) for _ in range(1 + max(bonus_dice, penalty_dice))]
                    if bonus_dice > 0:
                        final_tens = min(rolls[:1 + bonus_dice])
                        roll_type = get_output("dice.roll_types.bonus")
                    else:
                        final_tens = max(rolls[:1 + penalty_dice])
                        roll_type = get_output("dice.roll_types.penalty")
                    subtotal = final_tens * 10 + unit
                    roll_result = f"{expr} = [D100: {base_tens * 10 + unit}, {roll_type}: {', '.join(map(str, rolls))}] → {subtotal}"

                else:
                    # 普通骰子
                    rolls = [random.randint(1, dice_faces) for _ in range(dice_count)]
                    sorted_rolls = sorted(rolls, reverse=True)
                    selected_rolls = sorted_rolls[:keep_highest]
                    subtotal_before_mod = sum(selected_rolls)

                    if keep_highest < dice_count:
                        kept = " ".join(map(str, sorted_rolls[:keep_highest]))
                        dropped = " ".join(map(str, sorted_rolls[keep_highest:]))
                        all_rolls = " ".join(map(str, sorted_rolls))
                        roll_result = get_output(
                            "dice.keep_highest",
                            dice_count=dice_count, dice_faces=dice_faces,
                            keep_highest=keep_highest, subtotal=subtotal_before_mod,
                            kept=kept, dropped=dropped, rolls=all_rolls
                        )
                    else:
                        roll_result = get_output("dice.normal_dice", dice_count=dice_count, dice_faces=dice_faces, subtotal=subtotal_before_mod, rolls=' + '.join(map(str, rolls)))

                    if modifier:
                        try:
                            op = modifier[0]
                            val = int(modifier[1:])
                            if op == '+':
                                subtotal = subtotal_before_mod + val
                            elif op == '-':
                                subtotal = subtotal_before_mod - val
                            elif op == '*':
                                subtotal = subtotal_before_mod * val
                            else:
                                return None, get_output("dice.modifier_error", modifier=modifier), False
                            roll_result = get_output("dice.dice_with_modifier", dice_count=dice_count, dice_faces=dice_faces, modifier=modifier, subtotal=subtotal_before_mod, rolls=' + '.join(map(str, rolls)), total=subtotal)
                        except (ValueError, ArithmeticError):
                            return None, get_output("dice.modifier_error", modifier=modifier), False
                    else:
                        subtotal = subtotal_before_mod

            # 计算单次掷骰的表达式
            if roll_total is None:
                roll_total = subtotal
            else:
                if operator == "+":
                    roll_total += subtotal
                elif operator == "-":
                    roll_total -= subtotal
                elif operator == "*":
                    roll_total *= subtotal

            # 存储格式化骰子结果
            if i == 0:
                formatted_parts.append(f"{roll_result}")
            else:
                formatted_parts.append(f"{operator} {roll_result}")

        # 最终格式化输出
        if is_multi_roll:
            results.append(f"{'  '.join(formatted_parts)} = {roll_total}")
        else:
            results.append(f"{'  '.join(formatted_parts)} = {roll_total}")
        total = roll_total

    return total, "\n".join(results), is_multi_roll


def handle_roll_dice(expression: str, user_id: str = None, name: str = None, remark=None):
    """处理骰子表达式，返回格式化后的掷骰结果字符串。"""
    total, result_message, is_multi_roll = parse_dice_expression(expression)
    if total is None and not is_multi_roll:
        return get_output("dice.normal.error", error=result_message)
    if is_multi_roll:
        if remark:
            return get_output("dice.multi_roll.success_remark", result=result_message, name=name, remark=remark)
        return get_output("dice.multi_roll.success", result=result_message, name=name)
    if remark:
        return get_output("dice.normal.success_remark", result=result_message, total=total, name=name, remark=remark)
    return get_output("dice.normal.success", result=result_message, total=total, name=name)


def roll_hidden(message: str = None):
    """私聊掷骰，返回格式化字符串。"""
    default_dice = get_config("dice.default_faces", 100)
    message = message.strip() if message else f"1d{default_dice}"
    total, result_message, is_multi_roll = parse_dice_expression(message)
    if total is None and not is_multi_roll:
        return get_output("dice.hidden.error", error=result_message)
    return get_output("dice.hidden.success", result=result_message)


def roll_attribute(skill_name, skill_value, group_id, name):
    """普通技能判定"""
    try:
        skill_value = int(skill_value)
    except ValueError:
        return get_output("skill_check.error.normal", skill_name=skill_name)

    tens_digit = random.randint(0, 9)
    ones_digit = random.randint(0, 9)
    roll_result = 100 if (tens_digit == 0 and ones_digit == 0) else (tens_digit * 10 + ones_digit)

    result = get_roll_result(roll_result, skill_value, str(group_id))

    return get_output(
        "skill_check.normal",
        skill_name=skill_name,
        roll_result=roll_result,
        skill_value=skill_value,
        result=result,
        name=name
    )


def roll_attribute_penalty(dice_count, skill_name, skill_value, group_id, name):
    """技能判定（惩罚骰）"""
    try:
        dice_count = int(dice_count)
        skill_value = int(skill_value)
    except ValueError:
        return get_output("skill_check.error.penalty", skill_name=skill_name)

    ones_digit = random.randint(0, 9)
    new_tens_digits = [random.randint(0, 9) for _ in range(dice_count)]
    new_tens_digits.append(random.randint(0, 9))

    if 0 in new_tens_digits and ones_digit == 0:
        final_y = 100
    else:
        final_tens = max(new_tens_digits)
        final_y = final_tens * 10 + ones_digit

    result = get_roll_result(final_y, skill_value, str(group_id))

    return get_output(
        "skill_check.penalty",
        skill_name=skill_name,
        new_tens_digits=new_tens_digits,
        final_y=final_y,
        skill_value=skill_value,
        result=result,
        name=name
    )


def roll_attribute_bonus(dice_count, skill_name, skill_value, group_id, name):
    """技能判定（奖励骰）"""
    try:
        dice_count = int(dice_count)
        skill_value = int(skill_value)
    except ValueError:
        return get_output("skill_check.error.bonus", skill_name=skill_name)

    ones_digit = random.randint(0, 9)
    new_tens_digits = [random.randint(0, 9) for _ in range(dice_count)]
    new_tens_digits.append(random.randint(0, 9))

    filtered_tens = [tens for tens in new_tens_digits if not (tens == 0 and ones_digit == 0)]
    if not filtered_tens:
        final_tens = 0
    else:
        final_tens = min(filtered_tens)

    final_y = final_tens * 10 + ones_digit

    result = get_roll_result(final_y, skill_value, str(group_id))

    return get_output(
        "skill_check.bonus",
        skill_name=skill_name,
        new_tens_digits=new_tens_digits,
        final_y=final_y,
        skill_value=skill_value,
        result=result,
        name=name
    )


def get_roll_result(roll_result: int, skill_value: int, group: str):
    """根据掷骰结果和技能值计算判定结果文本（COC规则）。"""
    try:
        rule = get_great_sf_rule(group)
    except Exception:
        return get_output("coc_roll.results.error", error="Failed to fetch rule")

    validation_prefix = ""
    if great_success_range(50, rule)[0] <= 0:
        set_great_sf_rule(GREAT_SF_RULE_DEFAULT, group)
        validation_prefix += get_output("coc_roll.results.reset", rule=GREAT_SF_RULE_STR[GREAT_SF_RULE_DEFAULT])

    if roll_result in great_success_range(skill_value, rule):
        return validation_prefix + get_output("coc_roll.results.great_success")
    elif roll_result <= skill_value / 5:
        return validation_prefix + get_output("coc_roll.results.extreme_success")
    elif roll_result <= skill_value / 2:
        return validation_prefix + get_output("coc_roll.results.hard_success")
    elif roll_result <= skill_value:
        return validation_prefix + get_output("coc_roll.results.success")
    elif roll_result in great_failure_range(skill_value, rule):
        return validation_prefix + get_output("coc_roll.results.great_failure")
    else:
        return validation_prefix + get_output("coc_roll.results.failure")


def fireball(ring: int = 3):
    """施放 n 环火球术，返回伤害字符串。"""
    if ring < 3:
        return get_output("fireball.low")
    base_dice = get_config("dice.fireball.base_dice", 8)
    dice_per_ring = get_config("dice.fireball.dice_per_ring", 1)
    rolls = [random.randint(1, 6) for _ in range(base_dice + (ring - 3) * dice_per_ring)]
    total_sum = sum(rolls)
    damage_breakdown = " + ".join(map(str, rolls))
    return get_output(
        "fireball.result",
        ring=ring,
        breakdown=damage_breakdown,
        total=total_sum
    )


# 运势等级映射：按 COC 大成功/成功/失败/大失败逻辑映射到大吉~大凶
# 大成功 ~5% (1-5)，极难 ~10% (6-15)，困难 ~15% (16-30)
# 普通成功 ~25% (31-55)，接近失败 ~25% (56-80)
# 凶 ~15% (81-95)，大失败 ~5% (96-100)
FORTUNE_LEVELS = [
    (5, "大吉"),
    (15, "吉"),
    (30, "中吉"),
    (55, "小吉"),
    (80, "末吉"),
    (95, "凶"),
    (100, "大凶"),
]

FORTUNE_REPLIES = {
    "大吉": "今天的运势极佳！做什么都会很顺利，是抽卡、跑团、告白的好日子！🍀",
    "吉": "运势相当不错~ 事情大多会朝着好的方向发展，保持信心吧！✨",
    "中吉": "运势中等偏上，虽然不会事事顺遂，但努力就会有回报哦~",
    "小吉": "平平淡淡才是真，今天适合稳扎稳打，不宜冒进。😊",
    "末吉": "运势稍低，可能会遇到一些小麻烦，小心为上，别太勉强自己~",
    "凶": "今天运气不太好呢...尽量避免重要决策，低调度过吧。💦",
    "大凶": "大凶之兆！今天请务必谨慎行事，或许宅在家里是最好的选择...😱",
}


def _get_fortune(rp: int):
    """根据 rp 值 (1-100) 获取运势等级和对应回复。"""
    for threshold, level in FORTUNE_LEVELS:
        if rp <= threshold:
            return level, FORTUNE_REPLIES[level]
    return "末吉", FORTUNE_REPLIES["末吉"]  # fallback


def roll_RP(user_id: str):
    """今日RP（运势），返回字符串。"""
    max_rp = get_config("dice.rp.max_value", 100)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    RP_str = f"{user_id}_{today}"
    hash = hashlib.sha256(RP_str.encode()).hexdigest()
    rp = int(hash, 16) % max_rp + 1
    fortune, reply = _get_fortune(rp)
    return get_output("rp.today", rp=rp, fortune=fortune, reply=reply)
