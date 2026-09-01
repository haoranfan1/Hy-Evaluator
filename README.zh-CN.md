# Hy3 过程评估工作台

[English](README.md) | 简体中文

> 腾讯犀牛鸟开源实战任务（项目二：可验证场景 — 过程评估与错误定位）的个人参赛作品。
> 本仓库并非腾讯官方发布。

一个评估混元（Hy3）编码智能体在 SWE-bench Verified 上运行**过程**——而不仅是结果——的
Web 工作台。Hy3 通过 mini-SWE-agent 与 Harbor（ATIF v1.7 步骤轨迹）修复真实仓库问题；
工作台随后结合确定性证据通道、固定配置的 Hy3 语义评审通道以及程序化盲评的人工复核，
判断过程是否有效、定位第一处错误步骤、按文档化分类法归类、发现"结果对、过程有问题"的
运行，并以冻结的人工标注度量评估器自身的可靠性。

## 已验证的核心结论

来自冻结的八任务切片（`day8-slice-v1`，三个官方难度档）。带分子、分母、排除项与来源标注的
完整数字见[评估报告](docs/REPORT.md)。

- 官方验证器判定 **8/8 任务结果通过**，但在已裁定的盲评人工标注下仅 **4/8 过程有效**。
  每个被确认无效的运行都在过程中修改了受保护的评分测试文件。
- **结果准确率对一整类行为完全失明**：易任务上智能体随意修改评分测试（0/3 过程有效），
  难任务上则不碰（2/2）。
- 评估器实测的失效模式经两轮记录在案的修复（`workbench-evaluator-v2`，随后 `v3`）解决，
  每轮均以对照冻结标注的回归卡验证：**误报 3/4 → 0/4，第一处错误精确定位 0/4 → 4/4，
  检出 4/4 保持，语义覆盖 4/8 → 8/8**（对超长轨迹做有界压缩——只摘录真实产物；诚实弃权
  仍是兜底）。
- 固定的评审配置稳定：在三个输入（含一条压缩后的超长轨迹）上的 **十五次记录会话中，结论、
  第一处错误步骤与类别全部一致**，并在真实运行上独立与人工标注的步骤吻合。

## 快速开始

离线验证——无需凭证、不调用模型（测试套件以脚本替代评审模型）：

```bash
./scripts/uv-local python install 3.12
./scripts/uv-local sync --all-groups
./scripts/uv-local run pytest -q
```

```bash
cd frontend && npm ci && npm test
```

启动工作台（FastAPI 监听 `127.0.0.1:8000`，界面在 `127.0.0.1:5173`）：

```bash
./scripts/uv-local run hy3-workbench
```

```bash
cd frontend && npm run dev
```

如需实时语义评估，将 `.env.example` 复制为被忽略的 `.env` 并填入三个 Hy3 配置值；未配置时
API 以诚实的降级状态运行（健康检查报告评审模型未配置，评估直接拒绝而不是编造结论）。实时的
Harbor/SWE-bench 流水线及其 Docker 门禁见[开发环境设置](docs/DEVELOPMENT_SETUP.md)与
[报告 §9](docs/REPORT.md)。

界面默认英文，可在页眉切换为中文，并支持浅色/深色主题。

### 过程门禁（可用于 CI）

`scripts/process_gate.py` 将已存储的过程结论转换为退出码，使流水线可以基于过程有效性——
而不只是结果——设置门禁。它只读取已持久化的记录，绝不重新评估：`0` 有效 · `2` 无效 ·
`3` 不确定 · `4` 尚未评估 · `5` 未知运行。

```bash
./scripts/uv-local run python scripts/process_gate.py --run run-fixture-invalid-first-error --json
```

## 证据索引

| 证据 | 位置 |
| --- | --- |
| 分析报告：方法、指标、案例研究、局限 | [docs/REPORT.md](docs/REPORT.md) |
| 逐条需求审计 + 干净环境记录 | [docs/REQUIREMENTS_AUDIT.md](docs/REQUIREMENTS_AUDIT.md) |
| ≤2 分钟演示脚本（提交时由操作者录制） | [docs/DEMO.md](docs/DEMO.md) |
| 冻结切片协议（选取、盲评、运行配置） | [data/evaluation-slices/day8-slice-v1.json](data/evaluation-slices/day8-slice-v1.json) |
| 环境 / 参考补丁预言门禁 | [data/environment-checks/](data/environment-checks/) |
| 汇总 + 逐运行结果（确定性导出） | [results/](results/) |
| 人工检查记录（盲评标注 + 裁定） | [results/human_reviews.jsonl](results/human_reviews.jsonl) |
| 评估器 v2/v3 对照冻结标注的回归卡（界面 `/regressions` 页可视化） | [results/regression/](results/regression/) |
| 评审模型稳定性记录（十五次会话） | [results/judge-stability/](results/judge-stability/) |
| 合成预言夹具（有效 / 无效 / 不确定） | [data/fixtures/](data/fixtures/) |

## 仓库结构

```text
.
├── data/                         # 夹具、冻结切片、环境检查（版本化证据）
├── docs/                         # 需求、报告、审计、设计、路线图、演示
├── frontend/                     # React/Vite 证据调试器与评审界面
├── results/                      # 已验证证据的脱敏确定性导出
├── scripts/                      # 可复现的流水线与维护入口
├── src/                          # FastAPI 应用与评估器源码
├── tests/                        # 离线测试套件（评估器、工作流、API、夹具）
├── .gitignore
├── README.md                     # 英文（默认）
├── README.zh-CN.md               # 本文件
└── 犀牛鸟开源-实战任务-混元大语言模型项目.pdf  # 原始任务说明
```

## 文档

- [文档索引](docs/README.md)
- [项目需求](docs/PROJECT_REQUIREMENTS.md)
- [报告 —— 已验证结果与案例研究](docs/REPORT.md)
- [需求审计 —— 交付冻结](docs/REQUIREMENTS_AUDIT.md)
- [演示](docs/DEMO.md)
- [路线图](docs/ROADMAP.md)
- [架构](docs/ARCHITECTURE.md)
- [评估器规格](docs/EVALUATOR_SPEC.md)
- [开发环境设置](docs/DEVELOPMENT_SETUP.md)
- [研究工作区](docs/research/README.md)

## 状态

第 1–10 天的工程工作已完成并通过审计。操作者的端到端人工复核与自录演示是交付打标前剩余的
步骤。逐日构建与验证历史记录在[路线图](docs/ROADMAP.md)中。

## 开发

项目使用由 `uv` 管理的仓库本地 Python 3.12 环境（始终通过 `./scripts/uv-local` 调用），以及
由 `.node-version` 固定版本的 React/Vite 前端。隔离策略、配置、本地命令、Docker 门禁与主机
说明见[开发环境设置](docs/DEVELOPMENT_SETUP.md)。

请勿向本仓库添加真实凭证。将 `.env.example` 复制为被忽略的 `.env` 文件，并在本地设置 Hy3
凭证。
