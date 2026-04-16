# LioModChineseTranslateTool

一个快速、简易的 Minecraft Mod 汉化工具：选择 `.jar`，填写大模型接口配置，一键生成带 `zh_cn.json` 的汉化 Mod 包。

## 演示视频

[![演示视频](assets/demo_video.svg)](http://bilibili.com/video/BV1XTdhB5ENz/)

如果链接失效，可以在仓库 Issues 留言，我再补一个可用的演示链接或上传到 GitHub Releases。

## 快速开始（使用方法优先）

### 1) 安装依赖

```bash
pip install customtkinter openai
```

### 2) 启动程序

```bash
python main.py
```

### 3) 界面操作步骤

1. 点击 `选择文件`，选择要汉化的 Mod `.jar`
2. 在 `LLM 配置` 填写 `API Key` 和 `Base URL`
3. 点击 `检查 API Key`，鉴权成功后 `开始处理` 会亮起
4. 点击 `开始处理`，等待完成弹窗
5. 输出文件默认命名为：`原文件名-chinese.jar`（可点击输出区域复制路径）

## 使用说明（你最需要关注的行为）

- 只会翻译一个语言源文件：优先选 `en_us.json` / `en-us.json`，否则选扫描到的第一个 locale JSON
- 翻译输出固定写为 `zh_cn.json`
- 生成 `zh_cn.json` 后，会删除同目录下其他 `.json` 语言文件（因此包内通常只保留 `zh_cn.json`）
- 只翻译包含英文字母的字符串；不含英文字母的条目会跳过
- 对重复原文启用缓存，减少重复请求
- 会尽量保留占位符（`%s`、`{name}`、`\n`、`§a` 等）；校验失败的条目保留原文继续跑

## 一键更新 GitHub 仓库

双击运行 [update_github.bat](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/update_github.bat)：

- 自动 `git add -A`
- 有变更才会自动 commit
- 自动 `git pull --rebase origin main`
- 自动 `git push origin main`

适合你每次改完 README / 代码后快速同步到 GitHub。

## 常见问题

### 1. 为什么“开始处理”按钮是灰色的？

原因通常是还没有完成鉴权。

请检查：

- 是否填写了 `API Key`
- 是否点击了 `检查 API Key`
- 鉴权是否成功
- 是否修改过 `API Key` 或 `Base URL`

注意：只要 `API Key` 或 `Base URL` 改动过，就需要重新鉴权。

### 2. 为什么提示鉴权失败？

可能原因：

- `API Key` 错误
- `Base URL` 不正确
- 当前服务不兼容 OpenAI SDK 调用方式
- 当前服务不支持 `deepseek-chat`
- 网络连接异常

### 3. 没装 Java 能不能用？

可以。

项目会优先使用 Java 的 `jar` 工具；如果找不到，会自动回退到 Python 的 `zipfile` 进行打包。

### 4. 为什么翻译后包里只剩 `zh_cn.json`？

这是当前实现的默认行为。程序会清理同目录的其他 `.json` 语言文件，只保留新生成的 `zh_cn.json`。

### 5. 翻译过程中个别条目没有变成中文？

常见原因：

- 该字符串不含英文字母，被自动跳过
- 模型返回异常，程序保留了原文
- 占位符校验未通过，程序放弃该条翻译

## 运行环境

- Python 3.10+
- Windows
- 可访问你配置的模型接口服务

依赖项：

- `customtkinter`
- `openai`
- Python 标准库 `tkinter`

## 工作原理（开发者）

<details>
<summary>展开查看</summary>

### 处理流程

流程定义在 [main.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/main.py) 的 `run_pipeline()`：

1. 解包 `.jar`（[unpack_jar.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/unpack_jar.py)）
2. 递归查找 locale JSON（[find_json.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/find_json.py)）
3. 选择目标源语言文件（优先 `en_us`）
4. 翻译 JSON 并输出 `zh_cn.json`（[translate_json.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/translate_json.py)）
5. 重新打包 `.jar`（[create_jar.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/create_jar.py)）

### 大模型调用

调用封装在 [call_llm.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/call_llm.py)：

- 使用 OpenAI SDK：`OpenAI(api_key=..., base_url=...)`
- 固定模型名：`deepseek-chat`
- 通过解析 `{"result": "..."}` 获取译文，并做占位符校验

### 运行期配置

[config.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/config.py) 当前只做“进程内存级”保存，不会落盘。

</details>

## 安全提示

- `API Key` 具有接口调用权限，不要硬编码到仓库里
- 如果后续做配置落盘，建议默认忽略配置文件并避免提交密钥

## 许可证

当前仓库没有提供 `LICENSE`（并且在 `.gitignore` 中忽略了 `LICENSE`）。

如果你准备开源或接受他人贡献，建议补充：

- `LICENSE`
- 贡献说明
- 版本发布说明

为了降低游戏文本格式被模型破坏的概率，项目实现了占位符校验逻辑。

检测范围包括：

- printf 风格占位符，如 `%s`、`%d`、`%.2f`
- 花括号变量，如 `{name}`、`{0}`
- 转义字符，如 `\n`、`\t`
- Minecraft 颜色或格式代码，如 `§a`

流程如下：

1. 先要求模型以严格 JSON 返回
2. 解析返回内容中的 `{"result": "..."}` 结构
3. 对比原文与译文中的占位符集合
4. 若不匹配，则视为失败并重新尝试
5. 如果多次尝试仍失败，则保留原文

相关实现位于 [call_llm.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/call_llm.py) 的 `translate()`、`_extract_placeholders()` 与 `_has_matching_placeholders()`。

## 配置行为

配置定义位于 [config.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/config.py)。

当前配置项仅包括：

- `api_key`
- `base_url`

需要特别注意：

- 当前配置保存在进程内存中
- 没有写入磁盘配置文件
- 程序关闭后不会自动持久化

也就是说，本项目目前是“运行期保存”，不是“跨重启保存”。

## 项目结构

```text
LioModChineseTranslateTool/
├─ main.py            # GUI 界面、任务线程、流程编排
├─ call_llm.py        # API 鉴权、模型调用、翻译结果解析与占位符校验
├─ translate_json.py  # JSON 遍历、逐条翻译、缓存、进度回调、输出 zh_cn.json
├─ find_json.py       # 递归查找符合 locale 命名规则的语言文件
├─ unpack_jar.py      # 解包 JAR
├─ create_jar.py      # 重新打包 JAR
├─ config.py          # 运行期配置
├─ icon.ico           # Windows 图标
└─ icon.png           # 通用图标
```

## 核心模块说明

### `main.py`

职责：

- 创建并管理桌面界面
- 响应用户操作
- 启动后台线程
- 将翻译进度同步到界面
- 串联整个处理流程

关键点：

- 使用 `queue.Queue` 传递后台线程事件
- 使用 `threading.Thread` 避免界面卡死
- API 鉴权成功前禁用开始按钮
- 支持点击输出区域复制输出路径

### `translate_json.py`

职责：

- 加载源 JSON
- 遍历所有字符串值
- 调用翻译函数
- 写出 `zh_cn.json`

关键点：

- 支持嵌套字典和数组
- 使用缓存减少重复翻译
- 按需发送 `start`、`progress`、`warning`、`done` 事件

### `call_llm.py`

职责：

- 校验 API 可用性
- 封装模型调用
- 尽量从模型输出中解析合法 JSON
- 检查占位符一致性

关键点：

- 容忍模型返回带代码块或额外文本的 JSON
- 优先使用默认翻译提示词
- 出现占位符问题时回退到更严格的提示词再试

### `create_jar.py`

职责：

- 将处理后的目录重新打包为 `.jar`

关键点：

- 优先调用 Java `jar`
- 失败时自动回退为 ZIP 打包

## 已知限制

在实际使用前，建议先了解这些限制：

- 只会处理一个被选中的语言 JSON，不会同时融合多个语种来源
- 默认优先 `en_us.json`，如果 Mod 只有其他语言包，翻译质量可能受源语言影响
- 只要字符串中没有英文字母，就不会进入翻译流程
- 翻译结果依赖所用模型质量，术语一致性不一定稳定
- 当前默认模型名写死为 `deepseek-chat`
- 配置不会持久化到磁盘
- 输出时会删除同目录其他语言 JSON 文件
- 某些特殊文本格式即便通过占位符校验，语义上仍可能需要人工润色

## 常见问题

### 1. 为什么“开始处理”按钮是灰色的？

原因通常是还没有完成鉴权。

请检查：

- 是否填写了 `API Key`
- 是否点击了 `检查 API Key`
- 鉴权是否成功
- 是否修改过 `API Key` 或 `Base URL`

注意：只要 `API Key` 或 `Base URL` 改动过，就需要重新鉴权。

### 2. 为什么提示鉴权失败？

可能原因：

- `API Key` 错误
- `Base URL` 不正确
- 当前服务不兼容 OpenAI SDK 调用方式
- 当前服务不支持 `deepseek-chat`
- 网络连接异常

### 3. 没装 Java 能不能用？

可以。

项目会优先使用 Java 的 `jar` 工具；如果找不到，会自动回退到 Python 的 `zipfile` 进行打包。

### 4. 为什么翻译后包里只剩 `zh_cn.json`？

这是当前实现的默认行为。程序会清理同目录的其他 `.json` 语言文件，只保留新生成的 `zh_cn.json`。

### 5. 翻译过程中个别条目没有变成中文？

常见原因：

- 该字符串不含英文字母，被自动跳过
- 模型返回异常，程序保留了原文
- 占位符校验未通过，程序放弃该条翻译

## 开发与二次修改建议

如果你准备继续开发这个项目，常见修改点包括：

- 将 `config.py` 改为读写本地配置文件，实现真正的持久化
- 把模型名从 `deepseek-chat` 改为可配置项
- 增加术语表、提示词模板或自定义词典
- 为不同 Mod 适配更细粒度的语言文件筛选规则
- 增加“保留原语言文件”的开关
- 增加批量处理多个 JAR 的能力
- 加入日志输出，便于定位失败条目
- 增加 CLI 模式，方便脚本化使用

## 适合补充的工程文件

当前仓库还没有以下常见文件，如有需要可补充：

- `requirements.txt`
- `.gitignore`
- 打包说明文档
- 示例输入输出截图
- 发布版使用说明

## 安全提示

请注意：

- 你填写的 `API Key` 具有接口调用权限
- 不建议把带有真实 Key 的配置硬编码到源码中
- 如果后续增加配置文件持久化，建议至少避免将 Key 提交到版本控制

## 快速开始

如果你只想马上跑起来，可以直接照下面做：

```bash
pip install customtkinter openai
python main.py
```

然后在界面中：

1. 选择一个 Mod 的 `.jar`
2. 填写 `API Key`
3. 视需要修改 `Base URL`
4. 点击 `检查 API Key`
5. 点击 `开始处理`

## 许可证与说明

当前仓库中未看到明确的开源许可证文件。

如果你准备公开发布或接受他人贡献，建议补充：

- `LICENSE`
- 贡献说明
- 版本发布说明
