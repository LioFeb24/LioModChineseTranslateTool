# LioModChineseTranslateTool

一个用于将 Minecraft Mod 的语言文件自动翻译为简体中文并重新打包为 `.jar` 的桌面工具。

项目提供图形界面，用户只需要选择目标 Mod 文件、填写兼容 OpenAI SDK 的大模型接口配置并完成鉴权，即可自动执行以下流程：

1. 解包 Mod 的 `.jar` 文件
2. 递归查找语言包目录中的 locale JSON 文件
3. 自动选择待翻译语言文件，优先 `en_us.json` 或 `en-us.json`
4. 调用 DeepSeek 兼容接口逐条翻译文本
5. 生成 `zh_cn.json`
6. 删除同目录下其他语言 JSON 文件
7. 重新打包为新的中文 Mod 文件

## 项目定位

本项目适合以下场景：

- 某个 Mod 没有提供中文语言文件
- 你只想快速得到一个可用的汉化版本
- 你希望通过 GUI 完成整个流程，而不是手动解压、改 JSON、重新压缩

本项目不是通用的整包本地化平台，它当前聚焦于：

- 单个 Mod JAR 的处理
- 基于语言 JSON 的文本翻译
- DeepSeek 兼容的 Chat Completions 接口

## 功能特性

- 图形界面操作，适合非命令行用户
- 支持手动填写 `API Key` 和 `Base URL`
- 开始翻译前先进行 API 鉴权
- 自动扫描符合 locale 命名规则的 JSON 文件
- 优先翻译 `en_us.json` / `en-us.json`
- 递归处理嵌套对象与数组中的字符串
- 自动跳过不含英文字母的字符串
- 对重复文本启用缓存，避免重复调用模型
- 校验占位符，尽量保留 `%s`、`{name}`、`\n`、`§a` 等格式内容
- 翻译失败时保留原文并继续处理后续条目
- 优先使用 Java 的 `jar` 工具重新打包，不可用时自动回退到 Python `zipfile`

## 界面说明

应用主界面包含以下区域：

- `Mod文件`：选择待处理的 `.jar` 文件
- `汉化Mod文件`：输出路径展示区，默认在原文件名后追加 `-chinese.jar`
- `LLM 配置`：填写模型接口配置
- `检查 API Key`：验证当前接口是否可用
- `开始处理`：启动完整汉化流程
- `翻译进度`：显示当前处理阶段、总量、已完成数量、失败数量和当前条目路径
- `原文 / 译文`：实时展示当前翻译项的输入与输出

## 运行环境

建议环境：

- Python 3.10 或更高版本
- Windows
- 可正常访问你配置的模型接口服务

依赖项：

- `customtkinter`
- `openai`
- Python 标准库中的 `tkinter`

说明：

- 如果你的 Python 环境没有可用的 `tkinter`，GUI 将无法启动
- 如果系统安装了 Java 且 `PATH` 或 `JAVA_HOME` 中可找到 `jar`，将优先使用 Java 打包
- 即使没有 Java，项目仍可回退为 Python 原生 ZIP 方式打包 JAR

## 安装方式

先安装依赖：

```bash
pip install customtkinter openai
```

然后直接运行：

```bash
python main.py
```

## 使用方法

### 1. 启动程序

```bash
python main.py
```

### 2. 选择 Mod 文件

点击 `选择文件`，选择要处理的 `.jar` 文件。

程序会自动生成默认输出文件名，例如：

- 输入：`ExampleMod.jar`
- 输出：`ExampleMod-chinese.jar`

### 3. 配置大模型接口

在界面中填写：

- `API Key`
- `Base URL`

默认 `Base URL` 为：

```text
https://api.deepseek.com
```

这个地址来自 [config.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/config.py) 中的 `DEFAULT_BASE_URL`。

### 4. 检查 API Key

点击 `检查 API Key` 后，程序会使用 `deepseek-chat` 模型发起一次极小请求，用于确认：

- Key 是否填写
- 接口是否可连接
- 当前 `Base URL` 是否兼容 OpenAI SDK 调用方式

只有鉴权成功后，`开始处理` 按钮才会启用。

### 5. 开始处理

点击 `开始处理` 后，程序会自动执行完整流程：

1. 解包 JAR
2. 查找语言 JSON
3. 选定目标源语言文件
4. 翻译为简体中文
5. 生成 `zh_cn.json`
6. 重新打包为新的 JAR

处理完成后会弹窗提示输出文件路径。

## 翻译流程详解

整体流程定义在 [main.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/main.py) 的 `run_pipeline()` 中，逻辑如下：

### 1. 解包 JAR

使用 [unpack_jar.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/unpack_jar.py) 中的 `unpack_jar()` 解压目标 Mod。

底层实现基于 Python 标准库 `zipfile`，因为 JAR 本质上就是 ZIP 格式。

### 2. 查找可翻译语言文件

使用 [find_json.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/find_json.py) 中的 `find_json()` 递归扫描语言文件。

当前识别规则：

- 文件必须以 `.json` 结尾
- 文件名必须符合 `语言_地区.json` 或 `语言-地区.json`
- 例如：`en_us.json`、`zh_cn.json`、`pt-BR.json`、`es_419.json`

### 3. 选择目标语言文件

选择逻辑位于 [main.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/main.py) 的 `choose_target_json()`：

- 若找到 `en_us.json` 或 `en-us.json`，优先使用它
- 否则使用扫描结果中的第一个 locale JSON

这意味着如果某些 Mod 只有其他语种语言包，也会尝试从该语言包生成中文。

### 4. 翻译 JSON 内容

翻译逻辑位于 [translate_json.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/translate_json.py)。

核心行为如下：

- 递归遍历字典和列表中的所有字符串叶子节点
- 只翻译包含英文字母的字符串
- 不含英文字母的字符串直接跳过
- 对完全相同的原文启用缓存
- 每翻译一项就通过回调更新进度条和预览区域
- 某条翻译失败时保留原文，并继续后续任务

输出文件固定写为：

```text
zh_cn.json
```

### 5. 清理同目录其他语言文件

`translate_json()` 在写出 `zh_cn.json` 后，会调用 `_cleanup_sibling_json_files()` 删除同目录下除了目标文件以外的其他 `.json` 文件。

这表示输出 JAR 中，目标语言目录通常只会保留一个 `zh_cn.json`。

如果你希望同时保留原始英文或其他语种文件，需要先修改这段逻辑。

### 6. 重新打包 JAR

打包逻辑位于 [create_jar.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/create_jar.py)。

行为如下：

- 优先查找系统中的 `jar` 可执行文件
- 若 `PATH` 中存在 `jar`，直接调用
- 否则尝试从 `JAVA_HOME/bin` 中查找
- 若仍未找到，则自动回退到 Python `zipfile` 压缩方式

## 大模型调用说明

模型调用位于 [call_llm.py](file:///c:/Users/30848/Desktop/LioModChineseTranslateTool/call_llm.py)。

### 当前模型名

代码中固定使用：

```text
deepseek-chat
```

这意味着：

- 默认最适合直接配合 DeepSeek 使用
- 如果你使用其他兼容 OpenAI SDK 的网关，需确保该网关也支持这个模型名，或者自行修改源码

### 接口调用方式

项目通过 `OpenAI(api_key=..., base_url=...)` 构造客户端，并调用：

- `client.chat.completions.create(...)`

因此兼容条件通常是：

- 提供与 OpenAI SDK 兼容的 Chat Completions API
- 接收 `model`、`messages`、`timeout` 等参数

### 鉴权逻辑

`validate_api_key()` 会发送一个非常小的测试请求：

- 模型：`deepseek-chat`
- 用户消息：`ping`
- `max_tokens=1`

如果请求成功，就视为鉴权成功。

### 重试逻辑

真正翻译时，`call_llm()` 对以下异常做了自动重试：

- `APIConnectionError`
- `APITimeoutError`
- `RateLimitError`

最多重试 6 次，使用指数退避方式等待。

## 占位符保护机制

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
