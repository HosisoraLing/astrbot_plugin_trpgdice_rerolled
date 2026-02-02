# 更新日志 (Changelog)

所有项目的重要变更都会在此文件中记录。

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

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
