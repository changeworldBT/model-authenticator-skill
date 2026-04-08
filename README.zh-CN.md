# Model Authenticator Skill

[English](./README.md)

这是一个通过行为探针识别中转站、代理站、路由 API 背后真实模型的 skill，不盲信接口宣称的模型名。

这个仓库只包含一个可移植 skill，本体位于 `skills/model-authenticator/`。它主要解决一种常见问题：中转站声称提供高端模型，但实际返回的是更便宜的替代模型。

## 能做什么

- 通过多轮行为测试探测真实模型，而不是只看返回的 `model` 字段
- 支持 OpenAI 兼容、Anthropic 兼容、Gemini 风格三类接口
- 基于 JSON 纪律、工具调用行为、指令优先级、上下文保持、家族提示等特征做归因
- 在证据足够时给出强结论，在证据较弱时返回候选集
- 明确标记疑似降配或跨家族替换，并给出证据
- 在询问用户之前，优先自动发现本地已经配置好的 `model` 和 `base_url`

## 仓库结构

- `skills/model-authenticator/SKILL.md`：触发描述和运行流程
- `skills/model-authenticator/agents/openai.yaml`：可选 UI 元数据
- `skills/model-authenticator/references/`：评分规则和协议说明
- `skills/model-authenticator/scripts/probe_models.py`：主探针脚本
- `skills/model-authenticator/scripts/mock_model_server.py`：本地验证用 mock relay
- `skills/model-authenticator/scripts/test_probe_models.py`：集成测试

## 环境要求

- Python 3.11 或更新版本
- 一个可访问的待测端点
- 如果目标 relay 需要鉴权，则提供 API key；本地匿名网关可不提供

## 安装方式

把下面这个目录复制到你所用 agent 的本地 skills 目录：

```text
skills/model-authenticator
```

在当前这类 Codex 本地环境里，通常可以这样安装：

```powershell
Copy-Item -Recurse .\skills\model-authenticator "$HOME\.codex\skills\"
```

不同客户端的 skill 目录可能不同，但真正的 skill 本体就是 `skills/model-authenticator/`。

## 自动发现顺序

探针脚本会按这个顺序寻找配置：

1. CLI 参数
2. `MODEL_AUTH_*` 环境变量
3. `OPENAI_*`、`ANTHROPIC_*`、`GEMINI_*` 等 provider 环境变量
4. 当前工作目录下的 `.env.local` 和 `.env`
5. `~/.codex/config.toml`
6. `~/.config/opencode/opencode.jsonc`

如果你的 relay 已经在本地配置好了，通常可以直接零参数运行。

## 使用方式

### 零参数探测

```bash
python skills/model-authenticator/scripts/probe_models.py
```

### 显式指定 OpenAI 兼容端点

```bash
python skills/model-authenticator/scripts/probe_models.py --protocol openai --base-url https://example.com/v1 --api-key YOUR_KEY --model gpt-4o
```

### 显式指定 Anthropic 兼容端点

```bash
python skills/model-authenticator/scripts/probe_models.py --protocol anthropic --base-url https://example.com --api-key YOUR_KEY --model claude-3-7-sonnet
```

### 显式指定 Gemini 风格端点

```bash
python skills/model-authenticator/scripts/probe_models.py --protocol gemini --base-url https://example.com/v1beta --api-key YOUR_KEY --model gemini-2.0-flash
```

### 检测到替换时让进程失败

```bash
python skills/model-authenticator/scripts/probe_models.py --fail-on-mismatch
```

## 输出说明

脚本会输出 JSON，核心字段包括：

- `status`：`ok`、`partial` 或 `unreachable`
- `declared_model`：你要测试的声明模型
- `suspected_actual_model`：在置信度足够高时给出的单一强结论
- `candidate_models`：证据较弱时返回的候选排序
- `confidence`：综合置信度
- `risk_level`：`low`、`medium`、`high` 或 `unknown`
- `mismatch_detected`：是否疑似发生替换或降配
- `evidence`：支持结论的高价值证据
- `contradictions`：冲突项或连通性失败原因

如果 `status` 是 `unreachable`，不要推断真实模型，应该先修复连通性。

## 评分思路

当前 probe set 主要组合这些轻量特征：

- 严格 JSON 输出
- 极简输出服从性
- system 指令优先级
- 干扰块下的上下文锚点保持
- 工具调用纪律
- 家族提示探针

这些特征会与若干候选 profile 匹配，包括 OpenAI 高端、OpenAI 小模型、Anthropic Sonnet 风格、Gemini Flash 风格、Qwen instruct 风格、DeepSeek 风格等。

详细规则见：

- `skills/model-authenticator/references/fingerprint-rubric.md`
- `skills/model-authenticator/references/protocol-notes.md`

## 验证

运行仓库自带测试：

```bash
python skills/model-authenticator/scripts/test_probe_models.py
```

运行结构校验：

```bash
python C:\Users\84915\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills/model-authenticator
```

## 局限性

- 这是行为归因，不是密码学意义上的证明
- 某些 relay 会重写或标准化响应，导致家族特征被抹平
- 中间件可能改变风格，但底层模型并没有变
- 单次会话可能不足以下结论；如果端点不稳定或协议支持不完整，建议重复探测

## 仓库地址

```text
https://github.com/changeworldBT/model-authenticator-skill
```
