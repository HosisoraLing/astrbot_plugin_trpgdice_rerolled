# 更新日志 (Changelog)

所有项目的重要变更都会在此文件中记录。

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

---

## [1.5.0] - 2026-07-22

### 🔧 架构重构：平台适配器抽象层

- **新增 `component/platform_adapter/` 模块** — 将平台特定 API 调用从 handler 中剥离，通过适配器模式统一接口
  - `base.py` — `BasePlatformAdapter` 抽象基类，定义 `send_group_message()`、`send_private_message()`、`get_nickname()`、`set_group_card()` 等接口
  - `__init__.py` — 工厂函数 `get_adapter(event)` 根据事件平台自动匹配合适的适配器，回退到 `UnknownPlatformAdapter`
  - `unknown.py` — 未知平台回退适配器，所有消息操作返回 `False`，触发调用方 `yield event.plain_result()` 兜底

- **handler 层全部改为通过适配器发送消息**
  - `dice_handler.py` / `coc_handler.py` 中的 `handle_roll_dice`、`roll_attribute`、`roll_attribute_bonus`、`roll_attribute_penalty`、`pc_grow_up` — 改为返回结果文本，不再直接调用 OneBot API
  - `router.py` 统一负责通过适配器发送 + fallback 逻辑
  - `character_handler.py` — `sn` 命令改为运行时检查 `adapter.supports_group_card`，而非硬编码 `"aiocqhttp"` 平台名
  - `router.py` — 撤回事件改为运行时检查 `adapter.supports_recall_events`

- **清理平台依赖**
  - `component/utils.py` — 移除 `get_sender_nickname()` 函数（原直接调用 OneBot `get_group_member_info`）
  - 所有 `client.api.call_action()` 调用已全部收敛至适配器层

### ✨ 新增平台支持

#### Telegram 适配器（实验性）

- 使用 `python-telegram-bot` ExtBot API
- `send_group_message` — `client.send_message()` 带 `reply_to_message_id`
- `send_private_message` — `client.send_message()` 私聊发送
- `get_nickname` — `client.get_chat_member()` 获取群成员名称
- `supports_recall_events` / `supports_group_card` — 不支持

#### QQ 官方机器人适配器（实验性）

- 使用 `qq-botpy` (botpy) Client API
- `send_group_message` — `bot.api.post_group_message()` 群聊消息
- `send_private_message` — C2C 消息通过 `/v2/users/{openid}/messages` API
- `get_nickname` — QQ 官方不暴露昵称查询，返回 `event.get_sender_name()`
- `supports_recall_events` / `supports_group_card` — 不支持

### 🐛 Bug 修复

- 修复 `telegram.py` 中 `from __future__ import annotations` 重复导入
- 修复 `telegram.py` 中缺失 `cast` 导入

### 🔧 架构重构

## [1.4.1] - 2026-07-17

#### 命令路由集中化

- **所有命令路由统一迁移至 `RouterMixin.identify_command()`**
  - 原因：AstrBot 中 `@event_message_type` 和 `@filter.command` 是互斥的调度链——注册前者后后者永远不会被调用
  - 这意味着 v1.3.0 中大部分 `@filter.command` 装饰的命令（`.coc` `.dnd` `.fireball` `.jrrp` `.setcoc` `.dicehelp` `.st` `.sn` `.pc` `.init` `.ed` `.log`）实际上从未工作过
  - 现所有命令（包括 `pc` / `log` 子命令）均通过 `identify_command()` 统一路由
- **修复异步生成器混用问题**
  - 原 `identify_command` 中 `await` 和 `yield` 混用导致整个函数变成异步生成器，部分分支无法正确执行
  - 重构后每个命令分支明确使用 `await`（API 直接发送）或 `async for ... yield`（委托给子方法）
- **修复多词命令空格剔除 Bug**
  - 原 `re.sub(r'\s+', '', ...)` 将 `.pc list` → `pclist`、`.log new` → `lognew`，导致 `cmd == "pc"` 永远为 False
  - 改为从原始消息（保留空格）提取命令词，空格剔除版仅用于 `ra/en/rd/r` 的数值解析


### 🐛 Bug 修复

- **修复 `.ra` 首次调用崩溃** - `coc_rule_init()` 仅在 `.setcoc` 中调用，`.ra` 首次执行时 SQLite `GroupRule` 表不存在。现 `set_great_sf_rule()` / `get_great_sf_rule()` 内部自动调用 `coc_rule_init()`
- **修复 `.log stat` 崩溃** - `JSONLoggerCore` 缺少 `stat_sessions()` 方法，已实现完整统计逻辑
- **清理调试日志残留** - 移除 `coc_handler.py` 和 `character_handler.py` 中的 `logger.info()` 调用

### ✨ 新增功能

#### 参数校验与错误提示

- `.ra` / `.rab` / `.rap` / `.en` 缺少技能名时显示用法提示
- `.st` 缺少参数时显示用法提示
- `.fireball` 非法环位时显示用法提示
- `.pc create` / `.pc change` / `.pc update` / `.pc delete` 缺少必填参数时显示用法提示
- `.pc` 无子命令时显示子命令列表
- `.log del` / `.log get` 缺少日志名时显示用法提示
- `.log` 无子命令时显示子命令列表

#### 日志统计

- 新增 `.log stat <日志名>` - 查看指定日志的消息数、掷骰数、参与人数、时长
- 新增 `.log stat --all` - 查看全部日志的汇总统计

### 📝 代码整理

- 所有 handler 模块添加 docstring，说明职责和 AstrBot 调度架构
- 标注 `@filter.command` 装饰器在当前架构下为死代码（保留作为文档和向前兼容）
- `main.py` 添加模块 docstring，Bot 昵称硬编码处添加 TODO 标注

### 🔧 新增配置模板

- `log.no_session_data` - 无会话数据
- `log.stat_header` - 统计表头
- `log.stat_line` - 统计行（变量: session_name, message_count, dice_count, user_count, duration）
- `log.stat_total` - 统计汇总（变量: session_count, total_messages, total_dice, total_users）

---

## [1.3.0] - 2026-05-20

### ✨ 新增功能

#### 连续掷骰

- 支持 `N#expr` 语法进行连续掷骰，例如 `.r6#4d6k3` 掷 4d6k3 共 6 次
- 连续掷骰结果以简略格式逐行显示，每次掷骰独立计算
- 最大连续掷骰次数受 `dice.max_repeat` 配置限制（默认 20 次）

### 🔧 配置更新

- 新增 `dice.multi_roll.success` 输出模板 - 连续掷骰成功输出
- 新增 `dice.multi_roll.success_remark` 输出模板 - 连续掷骰带备注输出

---

## [1.2.0] - 2026-04-15

### ✨ 新增功能

#### LLM 美化模式

- 新增 `llm_mode` 配置节（启用开关、模型 ID、系统提示词）
- 所有掷骰相关指令（`.r` `.rv` `.rh` `.ra` `.rap` `.rab` `.sc` `.ti` `.li` `.en` `.coc` `.dnd` `.fireball` `.jrrp` `.ri`）均支持 LLM 美化输出
- 关闭时与原有模板输出完全一致，LLM provider 不可用时自动降级，不影响正常使用

#### LLM 工具函数（Function Calling）

- `roll_dice` - 掷骰子，支持所有骰子表达式
- `skill_check` - COC 技能检定
- `san_check` - 理智检定（自动更新人物卡）
- `roll_coc_character` - 生成 COC 调查员属性
- `roll_dnd_character` - 生成 D&D 冒险者属性
- `fireball_damage` - 计算火球术伤害
- `daily_luck` - 查询今日运势
- `set_output_template` - 让 LLM 帮助修改输出模板（持久化保存）
- `set_llm_mode` - 让 LLM 开关美化模式并设置提示词

#### 插件本地覆盖层

- 新增 `data/plugin_overrides.json` 持久化存储，优先级高于 AstrBot 配置面板
- LLM 工具函数写入的输出模板、配置变更均保存于此，重启后保留

### 🐛 Bug 修复

- **修复保留最高骰输出格式** - `.r 10d6k5` 输出格式改为 `10d6k5=[保留 | 丢弃] = 总计`，不再重复显示总值
- **修复空 remark 触发 remark 模板** - `remark=""` 时改用普通模板，避免出现空的 `【】` 括号
- **修复 keep_highest 模板变量缺失** - 补传 `rolls` 变量，防止用户旧配置的格式字符串失败后原样输出

---

## [1.1.1] - 2026-04-15

### 🔒 安全修复

- **修复 SQL 注入漏洞** - `component/rules.py` 中 5 处 f-string SQL 全部改为参数化查询
- **移除不安全的代码执行** - `component/dice.py` 中骰子修正值计算改为安全的算术运算

### 🐛 Bug 修复

- **修复保留最高骰 (k) 不生效** - `.r 10d6k5` 现在正确保留最高的 5 个骰子（之前 `k` 被命令解析器错误当作备注）
- **修复 `pc.change` 错误提示不显示** - 模板 key 中的逗号修正为点号（`pc.change,missing` → `pc.change.missing`）
- **修复帮助文本转义错误** - `\m` 修正为 `\n`，补全多处缺失的换行符
- **修复 `end_current_round` 崩溃** - 添加先攻列表存在性检查，防止 `KeyError`
- **修复 `get_great_sf_rule` 崩溃** - 新群组首次使用技能检定时不再因 `fetchone()` 返回 `None` 而崩溃
- **修复 `status` 命令错误路径** - 错误提示现在正确通过 `event.plain_result()` 发送
- **修复 `.log get` 崩溃** - `export_session` 调用参数数量不匹配已修复
- **修复日志导出 `isDice` 字段** - 导出的 JSON 现在正确标记骰子消息（之前硬编码为 `False`）
- **修复日志导出时区** - 移除硬编码的 UTC+8 偏移，改为使用系统本地时区

### 🗑️ 移除

- **完全移除 `faker` 依赖** - 移除 `generate_names()` 函数、`.name` 命令及所有相关配置
- **移除未使用的 `component/initiative.py`** - `main.py` 中已有完整的先攻实现
- **清理死代码** - 移除未使用的导入（`datetime`、`hashlib`、`ast`、`json`、`uuid`、`sqlite3`）、废弃的 `fetch_group_rule()` 函数、已注释的旧 log 代码块、未使用的 `log_help_str` 和 `GLOBAL_SET` 变量

### ✨ 改进

- **先攻系统消息可自定义** - 所有先攻相关输出现在通过 `get_output()` 管理，可在配置中自定义
- **精简 `_conf_schema.json`** - 移除大量重复配置项，每个配置项的 description 中标注了可用的变量占位符
- **改进 `component/sanity.py` 封装** - 不再直接导入 `_config` 私有变量，改用新增的 `get_output_list()` 函数
- **`@register` 元数据对齐** - 插件 ID 和版本号现与 `metadata.yaml` 一致
- **更新 README.md** - 补充保留最高骰、先攻系统、配置说明等文档
- **裸 `except` 改为具体异常类型** - 提高错误定位能力

---

## [1.1.0] - 2026-02-02

### 🎯 主要变更（BREAKING CHANGE）
- **配置系统升级** - 从硬编码 YAML 升级为 AstrBot 官方 Schema-based 配置系统
  - 用户现在可以在 AstrBot 管理面板直观配置插件行为
  - 无需修改代码即可自定义所有配置项
  - 配置自动保存到 `data/config/astrbot_plugin_TRPG_config.json`

### ✨ 新增功能

#### 配置系统
- **创建 `_conf_schema.json`** - 完整的 JSON Schema 定义
  - 支持 8 个主要配置类别（output, dice, character, coc_rules, sanity, initiative, names, growth）
  - 包含 26 个详细配置项，涵盖骰子、角色生成、COC 规则等所有功能
  - 支持滑块、下拉列表、多行文本等多种 UI 组件

#### 代码改进
- **`component/output.py` 升级**
  - 实现 `set_config()` - 从 Schema 加载并初始化全局配置
  - 实现 `verify_config_initialization()` - 验证配置初始化状态
  - 实现 `get_config_info()` - 获取配置调试信息
  - 实现 `_load_schema()` - 自动加载 Schema 文件进行验证
  - 增强 `get_config()` - 支持多级 key 访问和默认值
  - 增强 `get_output()` - 支持模板格式化和错误处理

- **`main.py` 升级**
  - 更新 `DicePlugin.__init__(context, config)` 接收 `AstrBotConfig` 参数
  - 集成 `set_config(config)` 初始化配置系统
  - 添加 `from astrbot.api import AstrBotConfig` 导入

### 📋 配置项详情

#### output (7 项)
- skill_check - 技能判定输出模板
- rp - 运势系统输出
- fireball - 火球术输出
- coc_roll - COC 判定输出
- pc - 人物卡操作输出
- dice - 掷骰输出
- san - 理智系统输出

#### dice (4 项)
- `default_faces: 100` - 默认骰子面数（支持滑块 1-100）
- `max_count: 100` - 最大骰子个数（支持滑块 1-1000）
- `max_faces: 1000` - 最大骰子面数（支持滑块 10-10000）
- `vampire_default_difficulty: 6` - 吸血鬼骰默认难度（支持滑块 1-10）

#### character (7 项)
- `coc_three_d6_multiplier: 5` - 3d6 的倍数
- `coc_two_d6_bonus: 6` - 2d6+6 中的加值
- `coc_two_d6_multiplier: 5` - 2d6 的倍数
- `hp_formula: "(SIZ + CON) // 10"` - HP 计算公式
- `mp_formula: "POW // 5"` - MP 计算公式
- `san_formula: "POW"` - SAN 计算公式
- `dnd_drop_lowest: 1` - DND 4d6去最低个数

#### 其他配置类别
- **coc_rules** (1 项) - `default_rule: 2` COC 默认规则
- **sanity** (3 项) - 理智检定范围和疯狂症状配置
- **initiative** (2 项) - 先攻掷骰范围 (1-20)
- **names** (1 项) - `default_language: "cn"` 默认语言
- **growth** (1 项) - `success_threshold: 95` 成长成功阈值

### 🔧 使用方式

#### 获取配置值
```python
from component.output import get_config, get_output

# 获取数值配置
default_faces = get_config("dice.default_faces", 100)
hp_formula = get_config("character.hp_formula", "(SIZ + CON) // 10")

# 获取输出模板
output_text = get_output("dice.normal.success", name="张三", result="50")
```

#### 验证配置状态
```python
from component.output import verify_config_initialization, get_config_info

# 检查配置是否已初始化
if verify_config_initialization():
    print("配置已正确初始化")

# 获取配置调试信息
info = get_config_info()
print(info)
```

### 🔄 迁移指南

#### 从旧版本升级
1. 将新版本代码部署到 AstrBot plugins 目录
2. AstrBot 启动时会自动检测 `_conf_schema.json`
3. 根据 Schema 生成默认配置文件
4. 用户可在管理面板进行自定义配置
5. 无需修改现有的 `.log`、`.r`、`.st` 等命令

#### 配置源头
所有配置项现在完全来自于 `_conf_schema.json` 定义：
- 无硬编码配置值
- 配置流程完全透明可追踪
- 所有默认值都可在 Schema 中查看修改

### 📝 数据流
```
_conf_schema.json (Schema定义)
    ↓
AstrBot 启动 → 自动检测
    ↓
生成 AstrBotConfig 对象
    ↓
DicePlugin.__init__(context, config)
    ↓
set_config(config) 初始化
    ↓
运行时访问: get_config() / get_output()
    ↓
data/config/astrbot_plugin_TRPG_config.json (配置存储)
```

### 🚀 优势

- ✅ **用户友好** - 可视化配置界面，无需修改代码
- ✅ **版本控制** - 配置版本自动升级，向后兼容
- ✅ **透明可追踪** - 所有配置源头可追踪到 Schema 定义
- ✅ **易于维护** - 集中管理所有配置项
- ✅ **灵活扩展** - 支持添加新配置项无需修改代码

### ⚠️ 破坏性更改

- 配置系统从 YAML 文件切换为 Schema-based JSON
- 插件初始化签名变更：`__init__(context)` → `__init__(context, config)`
- `default_config.yaml` 现为可选参考文件，不再作为配置来源

### 🔐 备份与回滚

- GitHub 标签 `backup-before-config-update` 保存了升级前的版本
- 如需回滚：`git checkout backup-before-config-update`

---

## [1.0.3] - 2026-01-27

### 新增
- **日志导出功能改进** - 当使用 `.log end` 命令结束日志会话时，机器人现在会自动将日志文件发送到聊天窗口供用户下载
  - 日志以JSON格式导出，包含时间戳、用户名、消息内容和图片链接
  - 支持被动消息（反馈式消息）的标准API调用

### 改进
- **日志系统优化**
  - 优化 `export_session()` 方法，提高文件生成的可靠性
  - 改进错误处理，提供更详细的错误信息反馈
  - 添加文件导出失败和发送失败的错误提示

### 修复
- **修复异步处理问题** 
  - 修复 `cmd_log_end()` 中 `MessageEventResult` 不能用 `await` 的错误
  - 改进 `end_session()` 方法的返回值设计，不再混合数据和消息发送逻辑
  - 改进 `export_session()` 方法的返回值，改为返回 `(bool, str)` 表示成功状态和结果

### 架构改进
- **职责分离** - 重新设计日志导出流程
  - `log.py` 的方法现在专注于数据操作，不处理消息发送
  - `main.py` 的 `cmd_log_end()` 独立处理消息发送逻辑
  - 避免了异步操作的混乱，提高代码可维护性

### 配置
- 新增输出配置项：
  - `log.export_failed` - 日志导出失败提示
  - `log.send_file_failed` - 文件发送失败提示

### 技术细节
- 使用 `astrbot.api.message_components.File` 发送日志文件
- 实现异步文件处理流程，确保不阻塞聊天消息
- 文件命名格式：`{群ID}_{日志名}.json`
- 改进的异步流程：`end_session()` → `export_session()` → 文件发送

---

## [1.0.2] - 2026-01-XX

### 新增
- 日志记录功能框架搭建
- 支持创建、暂停、恢复和结束日志会话
- 支持查看活跃日志列表和删除日志记录

### 功能
- `.log new [日志名]` - 创建新的日志会话
- `.log on [日志名]` - 恢复已暂停的日志会话
- `.log off` - 暂停当前日志记录
- `.log end` - 结束日志会话（现已支持直接发送文件到聊天窗口）
- `.log list` - 查看所有日志会话
- `.log del <日志名>` - 删除指定日志
- `.log get <日志名>` - 导出指定日志

---

## [1.0.1] - 2026-01-XX

### 改进
- 完善人物卡系统的属性管理
- 优化骰子掷出结果的显示格式
- 改进技能检定的逻辑流程

---

## [1.0.0] - 2026-01-XX

### 初始发布
- 基础掷骰功能（支持D&D、CoC等标准规则）
- 人物卡管理系统
- 技能检定与对抗检定
- 自定义别名支持
- COC理智检定（带疯狂判定）
- 吸血鬼规则掷骰
- 自定义输出风格（通过config.yaml）
- 基础日志记录框架

---

## 使用说明

### 日志导出流程
1. 使用 `.log new` 创建新日志会话
2. 在会话中进行各种操作（掷骰、技能检定等），机器人会自动记录
3. 使用 `.log end` 结束日志，机器人会自动：
   - 关闭日志会话
   - 将记录的所有内容导出为JSON文件
   - **发送文件到聊天窗口**供用户下载

### 日志文件格式
```json
{
  "version": 1,
  "items": [
    {
      "nickname": "用户昵称",
      "IMUserId": "用户ID",
      "time": "2026/01/27 15:30:45",
      "message": "消息内容",
      "images": ["图片URL列表"],
      "isDice": false
    }
  ]
}
```

---

## 项目信息

- **项目名称**: 星星骰娘-重骰版
- **当前版本**: v1.0.3
- **作者**: 星空凌
- **基础项目**: [Astrbot_plugin_TRPGdice-Complete](https://github.com/WhiteEurya/Astrbot_plugin_TRPGdice-Complete)
- **仓库**: https://github.com/WhiteEurya/Astrbot_plugin_TRPGdice-Rerolled

---

## 贡献

欢迎提交问题报告(Issue)和改进建议(Pull Request)！
