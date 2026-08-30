Git 仓库地址：https://github.com/zuoxun520-arch/forge-coding-agent

项目名称：Forge Coding Agent。它是一个从零实现的轻量编程智能体：通过 OpenAI 兼容接口与大语言模型交互，读取和修改工作区文件、搜索文本、执行测试命令，并在最后给出可核验的结果。项目没有使用 LangChain、LlamaIndex、Agents SDK 等智能体框架；模型客户端仅负责请求，消息历史、工具定义、工具本地执行、循环终止、上下文压缩和错误处理均由本项目自行实现。

运行（Python 3.11+）：
1. `python -m venv .venv`；Windows 执行 `.venv\\Scripts\\Activate.ps1`；
2. `pip install -e ".[dev]"`；
3. 在环境变量中设置 `OPENAI_API_KEY`，可选设置 `AGENT_MODEL`、`AGENT_BASE_URL`；
4. 执行 `forge-agent --workspace . "请创建 hello.py 并运行测试"`。加入 `--yes` 可自动批准普通写入和命令；不加时逐次确认。
5. 运行测试：`python -m pytest`。测试不需要网络或真实 API key。
6. 可选前端：执行 `forge-agent --gui` 打开本地桌面界面，输入任务、选择工作区，查看模型/工具实时事件并处理审批。

安全与特色：文件工具的路径限制在工作区内；写文件采用临时文件加原子替换；精确替换要求匹配次数；命令在工作区作为 cwd 执行，设有超时、输出上限和常见高危模式阻断；重复失败调用会熔断；上下文压缩保持 assistant/tool 配对；运行记录写入 `.forge-agent/runs/` 并脱敏 API key/token。测试使用脚本模型，不需要网络或真实密钥即可覆盖端到端工具循环。

验收结果：16 项离线测试全部通过；真实模型完成了故障计算器的检查、修复和复测，且未修改测试。无凭据的过程记录见 `VALIDATION.md`。

演示建议：让 agent 新建一个带故意失败测试的小 Python 模块，先读取文件、定位失败、修改实现、运行 pytest，再展示最终结果和审计日志。视频控制在 2 分钟内，提交时将本文件与 MP4 压缩为“姓名.zip”。
