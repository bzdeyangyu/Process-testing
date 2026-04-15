# Process testing

一个面向“空间设计前期生产线”的 Python 原型项目，包含三部分能力：

- 通用单代理运行时 `src/agent_runtime`
- 面向展厅/展馆场景的设计工作流 `design_workflow`
- 可视化看板与本地服务 `dashboard` + `server.py`

当前仓库既能跑一个最小 MVP 流程，也保留了扩展到全流程 Demo、评测与知识库沉淀的结构。

## 项目能做什么

输入一段设计任务书后，项目可以按阶段产出：

- 结构化需求解析
- 材料/色彩/风格建议
- 视觉提示词与多方案出图任务
- 本地看板快照、事件日志和结果文件

完整 Demo 还预留了案例研究、概念提炼、故事线、功能分区、视频脚本、预算、汇报和进度管理等模块。

## 目录概览

```text
.
├─ src/agent_runtime/      # 运行时、状态存储、会话与看板能力
├─ design_workflow/        # 空间设计工作流、specialists、prompt 与工具
├─ dashboard/              # 前端看板页面
├─ demo/                   # MVP / full demo 启动入口
├─ evaluation/             # fixture 与评测脚本
├─ design_library/         # 设计参考与风格库
├─ wiki/                   # 项目知识页
├─ docs/                   # 系统设计与补充文档
└─ server.py               # 本地 HTTP 服务入口
```

## 环境准备

建议使用 Python 3.13。

安装依赖：

```bash
pip install -r requirements.txt
```

如需调用真实 LLM / 生图服务，先准备环境变量：

```bash
Copy-Item .env.example .env
```

需要的关键变量：

- `API_KEY`：LLM 服务 key
- `IMAGE_API_KEY`：生图服务 key；如果与 LLM 共用账号，可与 `API_KEY` 相同
- `IMAGE_PROVIDER`：可选 `cogview`、`wanx`、`mock`
- `LLM_BASE_URL`：默认是智谱接口
- `MODEL_NAME`：默认 `glm-4`

注意：仓库当前已改为仅从环境变量读取密钥，不再在代码中内置默认 key。

## 运行方式

运行最小 MVP：

```bash
python demo/run_mvp.py --no-llm --image-provider mock
```

运行完整 Demo：

```bash
python demo/run_demo.py
```

启动本地看板服务：

```bash
python server.py
```

启动后可访问：

- 看板首页：`http://localhost:8765/`
- 当前项目快照：`http://localhost:8765/boards/current`
- 历史运行记录：`http://localhost:8765/boards`

## 测试与评测

运行测试：

```bash
pytest
```

运行离线评测：

```bash
python evaluation/run_eval.py --scope mvp
```

## 当前项目定位

这个仓库更像“流程验证与架构样机”，而不是已经交付生产环境的成品。它的价值主要在于：

- 验证 agent runtime 的最小闭环
- 验证空间设计工作流的阶段拆分是否合理
- 验证看板、日志、产物落盘是否可追踪
- 为后续扩展多轮概念、知识库与人机协作留出骨架

## 相关文档

- 项目总结：`docs/PROJECT_SUMMARY.md`
- 系统设计：`docs/v1_system_design.md`
- 工作流图：`docs/workflow_diagram.md`
