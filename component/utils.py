import random
from faker import Faker

from .output import get_output, get_config

def generate_names(language="cn", num=5, sex=None):
    """
    批量生成随机名字，支持多语言和性别。
    """
    # 从配置获取默认语言和语言映射
    default_language = get_config("names.default_language", "cn")
    languages_config = get_config("names.languages", {})

    # 如果语言为空，使用默认语言
    if not language:
        language = default_language

    # 查找匹配的语言配置
    locale = None
    if language in languages_config:
        locale = languages_config[language].get("locale")
    else:
        # 检查别名
        for lang_key, lang_config in languages_config.items():
            aliases = lang_config.get("aliases", [])
            if language in aliases:
                locale = lang_config.get("locale")
                break

    # 如果没有找到匹配的配置，使用默认值
    if not locale:
        if language == "cn" or "中" in language or language == "zh" or language == "zh_CN":
            locale = "zh_CN"
        elif language == "en" or "英" in language or language == "en_GB":
            locale = "en_GB"
        elif language == "us" or "美" in language or language == "en_US":
            locale = "en_US"
        elif language == "jp" or "=日" in language or language == "ja_JP":
            locale = "ja_JP"
        else:
            locale = None

    fake = Faker(locale=locale) if locale else Faker()

    if sex == "男":
        names = [fake.name_male() for _ in range(num)]
    elif sex == "女":
        names = [fake.name_female() for _ in range(num)]
    else:
        names = [fake.name() for _ in range(num)]
    return names

def get_db_build(str_val, siz_val):
    """
    根据力量和体型计算DB和Build。
    """
    # 从配置获取DB/Build计算表
    db_build_table = get_config("db_build.table", [
        {"threshold": 64, "db": "-2D6", "build": -2},
        {"threshold": 84, "db": "-1D6", "build": -1},
        {"threshold": 124, "db": "+0", "build": 0},
        {"threshold": 164, "db": "+1D4", "build": 1},
        {"threshold": 204, "db": "+1D6", "build": 2},
        {"threshold": 999, "db": "+2D6", "build": 3}
    ])
    total = str_val + siz_val
    for item in db_build_table:
        if total <= item["threshold"]:
            return item["db"], item["build"]
    return "+0", 0

def roll_character():
    """
    生成一个CoC角色属性字典。
    """
    # 从配置获取CoC角色生成配置
    three_d6_config = get_config("character.coc.dice.three_d6", {"dice_count": 3, "dice_faces": 6, "multiplier": 5})
    two_d6_plus_6_config = get_config("character.coc.dice.two_d6_plus_6", {"dice_count": 2, "dice_faces": 6, "bonus": 6, "multiplier": 5})
    luck_config = get_config("character.coc.luck_dice", {"dice_count": 3, "dice_faces": 6, "multiplier": 5})

    def roll_three_d6():
        return sum(random.randint(1, three_d6_config["dice_faces"]) for _ in range(three_d6_config["dice_count"])) * three_d6_config["multiplier"]

    def roll_two_d6_plus_6():
        return (sum(random.randint(1, two_d6_plus_6_config["dice_faces"]) for _ in range(two_d6_plus_6_config["dice_count"])) + two_d6_plus_6_config["bonus"]) * two_d6_plus_6_config["multiplier"]

    def roll_luck():
        return sum(random.randint(1, luck_config["dice_faces"]) for _ in range(luck_config["dice_count"])) * luck_config["multiplier"]

    STR = roll_three_d6()
    CON = roll_three_d6()
    SIZ = roll_two_d6_plus_6()
    DEX = roll_three_d6()
    APP = roll_three_d6()
    INT = roll_two_d6_plus_6()
    POW = roll_three_d6()
    EDU = roll_two_d6_plus_6()

    HP = (SIZ + CON) // 10
    MP = POW // 5
    SAN = POW
    LUCK = roll_luck()
    DB, BUILD = get_db_build(STR, SIZ)
    TOTAL = STR + CON + SIZ + DEX + APP + INT + POW + EDU

    return {
        "STR": STR, "CON": CON, "SIZ": SIZ, "DEX": DEX,
        "APP": APP, "INT": INT, "POW": POW, "EDU": EDU,
        "HP": HP, "MP": MP, "SAN": SAN, "LUCK": LUCK,
        "DB": DB, "BUILD": BUILD, "TOTAL": TOTAL
    }

def format_character(data, index=1):
    """
    格式化CoC角色属性输出。
    """
    return (
        f"第 {index} 号调查员\n"
        f"力量: {data['STR']}  体质: {data['CON']}  体型: {data['SIZ']}\n"
        f"敏捷: {data['DEX']}  外貌: {data['APP']}  智力: {data['INT']}\n"
        f"意志: {data['POW']}  教育: {data['EDU']}\n"
        f"生命: {data['HP']}  魔力: {data['MP']}  理智: {data['SAN']}  幸运: {data['LUCK']}\n"
        f"DB: {data['DB']}  总和 : {data['TOTAL']} / {data['TOTAL'] + data['LUCK']}"
    )

def roll_4d6_drop_lowest():
    """
    掷4d6去最低，返回总和。
    """
    dnd_config = get_config("character.dnd.dice", {"dice_count": 4, "dice_faces": 6, "drop_lowest": 1})
    rolls = [random.randint(1, dnd_config["dice_faces"]) for _ in range(dnd_config["dice_count"])]
    return sum(sorted(rolls)[dnd_config["drop_lowest"]:])

def roll_dnd_character():
    """
    生成DND角色属性（六项，每项4d6去最低）。
    """
    attributes_count = get_config("character.dnd.attributes_count", 6)
    return [roll_4d6_drop_lowest() for _ in range(attributes_count)]

def format_dnd_character(data, index=1):
    """
    格式化DND角色属性输出。
    """
    data = sorted(data, reverse=True)
    return (
        f"第 {index} 位冒险者\n"
        f"[{data[0]}, {data[1]}, {data[2]}, {data[3]}, {data[4]}, {data[5]}] → 共计 {sum(data)}"
    )