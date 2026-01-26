# 星星骰娘-重骰版！

为 Astrbot 设计的 TRPG 骰子插件（参考 [Dice!](https://forum.kokona.tech/) 与 [海豹](https://dice.weizaima.com/) 的实现），提供掷骰、技能判定、人物卡管理与日志导出等常用功能，便于在群聊中进行跑团玩法支持。

为所有使用astrbot平台但想要有与其他骰娘相同体验的骰主设计。

基于[TRPGdice-Complete](https://github.com/WhiteEurya/Astrbot_plugin_TRPGdice-Complete)二次开发，提供配置文件以管理骰娘输出风格。

---

## 安装

1. 克隆仓库到本地：
   ```bash
   git clone https://github.com/WhiteEurya/Astrbot_plugin_TRPGdice-Complete.git
   ````

2. 将插件文件/目录放入 Astrbot 的插件目录（plugin folder）。

3. 启动或重启 Astrbot，确认控制台输出已加载本插件。

> 如果 Astrbot 有插件管理命令或配置文件，请根据 Astrbot 的文档把本插件添加到插件列表中。

---

## 功能

- **基础掷骰**
  - 支持常见的 DnD / CoC / 跑团检定
  - 支持算式，例如 `1d100+5`
  - 支持小众规则的掷骰 (目前已支持吸血鬼规则)

- **角色卡与检定**
  - 支持角色属性绑定
  - 一键进行 **技能检定**、**对抗检定**

- **自定义别名**
  - 角色名、技能名可自定义
  - 方便团队内的快速调用

- **日志与记录**
  - 自动保存跑团对话日志
  - 支持导出记录，便于存档和复盘

- **自定义风格回复**
  - 将所有回复集成到 `config.yaml` 中，方便自由修改

- **更多方便的功能**
  - 生成名字、抽取恐慌症状等...

---

## 快速使用示例

> 插件加载后，可在群聊或私聊中使用下列示例指令进行测试

* 基本掷骰（示例）：

  ```
  .r
  ```
* 技能判定（示例）：

  ```
  .ra侦查50
  ```
* 人物卡管理（示例）：
  本插件接收 **COC7版规则卡** 的 `.st` 输入

  ```
  .pc create <名字>
  .pc change <名字>
  .pc update 幸运+1
  .st 属性值
  ```

* 日志 / 会话（示例）：

  ```
  .log new <日志名>
  .log off
  .log on
  .log end
  ```

如需完整指令说明，请运行插件内置的帮助命令 `.dicehelp` 或查看源码中的命令实现部分。

---

## 许可

本项目采用 MIT 协议，欢迎自由使用与修改
