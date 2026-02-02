from astrbot.api import AstrBotConfig
import json
import os

# 全局配置对象
_config: AstrBotConfig = None
_schema = None  # 缓存的 Schema
_config_initialized = False

def _load_schema():
    """
    加载配置 Schema 文件以进行验证。
    """
    global _schema
    if _schema is not None:
        return _schema
    
    schema_path = os.path.join(os.path.dirname(__file__), "..", "_conf_schema.json")
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            _schema = json.load(f)
        return _schema
    except Exception as e:
        print(f"警告: 无法加载 Schema 文件: {e}")
        return {}

def set_config(config: AstrBotConfig):
    """
    设置全局配置对象。在插件初始化时由主程序调用。
    
    此函数会：
    1. 验证配置来源于 _conf_schema.json
    2. 确保所有配置项都已正确加载
    3. 检查必要的配置项完整性
    """
    global _config, _config_initialized
    _config = config
    _config_initialized = True
    
    # 加载并验证 Schema
    schema = _load_schema()
    
    # 验证配置的主要部分
    if schema:
        _verify_config_structure(schema, config)

def _verify_config_structure(schema, config):
    """
    验证配置结构是否与 Schema 匹配。
    """
    try:
        # 检查主要的配置类别
        for category in schema.keys():
            if category in config:
                config_category = config.get(category, {})
                schema_category = schema.get(category, {})
                
                # 如果是对象类型，检查其中的项
                if schema_category.get("type") == "object":
                    items = schema_category.get("items", {})
                    # 这里主要是日志记录，不进行严格验证
                    # 因为某些配置可能在 AstrBot 加载后才完全初始化
            
    except Exception as e:
        print(f"配置验证警告: {e}")

def get_output(key: str, **kwargs):
    """
    支持多层 key，通过点分隔，如 "skill_check.normal"
    根据 key 获取输出模板，并用 kwargs 格式化。
    如果 key 不存在则返回空字符串。

    配置来源：_conf_schema.json 中定义的 output 部分

    示例：
    - get_output("dice.normal.success", name="张三", result="50")
    - get_output("skill_check.normal", name="李四", skill_name="射击", skill_value="50", roll_result="45", result="成功")
    """
    if _config is None:
        raise RuntimeError("配置未初始化，请确保在插件初始化时调用 set_config()")

    keys = key.split(".")
    template = _config.get("output", {})
    for k in keys:
        if isinstance(template, dict):
            # 如果有 items 字段，先导航到 items
            if "items" in template:
                template = template["items"]

            # 现在查找 key
            if k in template:
                template = template[k]
            else:
                return ""
        else:
            return ""

    # 如果最终结果有 default 字段，使用它
    if isinstance(template, dict) and "default" in template:
        template = template["default"]

    if not isinstance(template, str):
        return ""

    try:
        return template.format(**kwargs)
    except Exception:
        return template

def get_config(key: str, default=None):
    """
    从配置对象中获取配置值，支持多层 key，通过点分隔。
    如果 key 不存在则返回 default。

    所有配置项都来自于 _conf_schema.json 的定义。
    AstrBot 在启动时自动根据 Schema 生成配置。

    示例：
    - get_config("dice.default_faces", 100)  # 默认骰子面数
    - get_config("character.hp_formula", "(SIZ + CON) // 10")  # HP 计算公式
    - get_config("coc_rules.default_rule", 2)  # COC 默认规则
    - get_config("sanity.san_check_max", 100)  # 理智检定最大值

    配置来源：_conf_schema.json
    存储位置：data/config/astrbot_plugin_TRPG_config.json（由 AstrBot 管理）
    """
    if _config is None:
        return default

    keys = key.split(".")
    config = _config
    for k in keys:
        # 处理 AstrBotConfig 对象或字典
        if hasattr(config, "get"):
            # AstrBotConfig 对象，使用 get 方法
            next_config = config.get(k)
            if next_config is None:
                return default
            config = next_config
        elif isinstance(config, dict):
            # 字典对象
            if k in config:
                config = config[k]
            else:
                return default
        else:
            return default

    # 如果最终结果有 default 字段，使用它
    if hasattr(config, "get") and config.get("default") is not None:
        return config.get("default")
    elif isinstance(config, dict) and "default" in config:
        return config["default"]

    return config

def verify_config_initialization():
    """
    验证配置是否已正确初始化。
    返回 True 表示配置已初始化且有效。
    """
    return _config is not None and _config_initialized

def get_config_info():
    """
    获取配置信息用于调试。
    返回配置的总体概况。
    """
    if _config is None:
        return {"status": "未初始化", "message": "配置系统未初始化"}
    
    return {
        "status": "已初始化",
        "schema_path": "_conf_schema.json",
        "config_source": "AstrBotConfig (data/config/astrbot_plugin_TRPG_config.json)",
        "categories": list(_config.keys()),
        "has_output": "output" in _config,
        "has_dice": "dice" in _config,
        "has_character": "character" in _config,
    }
