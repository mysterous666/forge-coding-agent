# Forge Coding Agent

Forge Coding Agent 是一个从零实现的轻量级编程智能体。项目仅使用 OpenAI 兼容接口与模型通信，智能体循环、消息历史、工具调用、本地执行、安全检查、上下文压缩、失败保护和审计记录均由项目自身实现，不依赖 LangChain、LlamaIndex 或 Agents SDK 等智能体框架。

## 项目亮点

- **完整智能体闭环**：模型可以自主读取代码、搜索文本、修改文件、运行命令，并根据执行结果继续分析直至完成任务。
- **安全的工作区操作**：文件访问被限制在指定工作区内；写入采用原子替换；精确替换会校验匹配次数；命令具有超时、输出上限和高危操作拦截。
- **可靠的上下文管理**：压缩长对话时保持 assistant/tool 消息配对，并通过重复调用熔断和最大步数限制避免无效循环。
- **过程可核验**：运行记录以 JSONL 格式写入 `.forge-agent/runs/`，敏感凭据会自动脱敏，便于复盘智能体的决策和工具执行过程。
- **桌面可视化界面**：提供本地 GUI，可选择工作区、输入任务、实时查看模型和工具事件、处理操作审批并获取最终结果。
- **离线测试完善**：16 项确定性测试无需网络或真实 API Key，覆盖核心工具循环和事件流程。

## 安装与运行

需要 Python 3.11 或更高版本：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:OPENAI_API_KEY = "你的 API Key"
forge-agent --workspace . --yes "创建 hello.py，使其输出 42，并运行测试"
```

不使用 `--yes` 时，写文件和执行命令都会请求人工确认。可通过 `AGENT_MODEL` 和 `AGENT_BASE_URL` 配置模型及 OpenAI 兼容接口。

启动桌面界面：

```powershell
forge-agent --gui
```

## 测试

```powershell
python -m pytest
```

测试不会调用网络 API。真实模型验收可使用 `examples/calculator_buggy` 中故意包含失败测试的示例项目，详细验证结果见 `VALIDATION.md`。

## 内置工具

项目提供 `list_files`、`read_file`、`search_text`、`write_file`、`replace_text` 和 `run_command` 六个核心工具，以较小且清晰的工具面覆盖常见编码任务。
