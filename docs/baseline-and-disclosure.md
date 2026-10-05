# 已有 OWP 基线与赛期开发披露

记录日期：2026-10-05。本文件是内部事实记录与英文披露草稿，不表示报名已经完成。

## 1. 读取范围

- 本次项目：`/Users/molin/Project/dorahacks/colosseum`。开始读取时为空目录。
- 已有代码：`/Users/molin/Project/openWorkProof`。
- 上游公开仓库：<https://github.com/dengyier/OpenWorkProof>。
- 当前 checkout HEAD：`0dbc32b648f31343a5f9ccabf678f1e1075e60f1`，提交时间 2026-09-12。
- `pyproject.toml` 声明版本：`1.4.0`、Apache-2.0。未在本次研究中核验 PyPI/npm 最新发布状态。

该 HEAD 早于本届开始时间，不能把其协议、集成和 57 秒视频写成赛事期间首次开发。

同时发现其他分支 `codex/runtime-process-guard-20260927` 包含 `5789276`（2026-09-27，本地进程授权保护）。它不是当前 HEAD，也不是本次已经实现的托管结算应用。若今后复用，需要核对真实来源和修改日期，明确披露，不能因提交日期处于赛期就自动算成本次成果。

## 2. 已有能力与新增缺口

| 项目 | 源码/文档证据 | 本次判断 |
| --- | --- | --- |
| 工作契约、授权与行动回执 | `README.md`、`src/openworkproof/` | 已有底座；不是本次新增 |
| 域分离 Ed25519 / JCS 签名 | `src/openworkproof/signing.py` | 已有；钱包兼容尚未验证 |
| 验收与验证绑定 | `acceptance.py`、`acceptance_bundle.py` | 已有；须接入实际客户 UI |
| 结算准备状态 | `settlement.py` | 只读状态，没有代币转账 |
| 外部 Acceptor 示例 | `external_acceptor.py` | 签名进程示例，不等于人工确认产品 |
| 服务交付切片 | `docs/commercial/verified-agent-delivery/README.md` | 已有目标用户与证据边界；不是付费客户证明 |
| OpenPay 商业方向 | `docs/superpowers/specs/2026-08-10-openworkproof-work-to-settlement-pitch-design.md` | 既有方案；不能当作已建支付网络 |
| Solana escrow、钱包验收、链上对账 | 本次目录尚无相关代码 | 必须新增并实际验证 |

OWP 的验证、接受、结算准备和资金转移必须分别记录。本次不能把 `ACCEPTED_FOR_SETTLEMENT` 或 `READY_FOR_SETTLEMENT_REVIEW` 改名冒充 `PAID`。

## 3. 原工作区未提交改动：全部保留

读取时 `git status --short`：

```text
 M README.md
 M agentteams/scripts/run_openworkproof_13_demo.py
 M src/openworkproof/repo_tools.py
 M tests/test_agentteams_acceptance_bundle_v13.py
 M tests/test_agentteams_workflow_v13.py
?? docs/integrations/runtime-process-guard.md
?? examples/runtime_process_guard.py
?? src/openworkproof/runtime_process_guard.py
?? supply-chain/images/candidates/57892761022653d8fdc256c022668ec157d6ff86.json
?? tests/test_runtime_process_guard.py
```

本次研究不修改、提交或打包上述改动。不要整目录复制 dirty 工作区作为“赛期新增源码”。后续实施先选固定依赖版本，并记录需要复用的补丁及来源。

当前 README 和 checkout 可能混有新改动；阅读当前文件的结果不自动代表公开 main 的相同内容。公开现状必须另外核验。

## 4. 本次验证边界

研究中完成以下聚焦检查：**141 passed，175.01 秒**（当前工作区）：

```bash
.venv/bin/python -m pytest -q \
  tests/test_settlement_readiness.py \
  tests/test_acceptance_decision_binding_v01.py \
  tests/test_acceptance_bundle_v01.py
```

这些检查只覆盖现有 OWP 的相关行为，不证明新合约、钱包集成、链上资金安全、整个测试套件或独立安全审计。

工具可行性：PATH 中发现 Node/npm，未发现 solana、anchor、rustc、cargo。这是当前 PATH 的检查，不断言整台机器不存在其他安装。本次没有安装或改动开发工具链。

## 5. 英文历史披露草稿

以下只陈述研究时已知事实；新模块完成前不能使用过去时宣称已交付。

> OpenWorkProof is a pre-existing open-source protocol for AI-agent work contracts, authorization, signed execution evidence, verification and acceptance. Its Core 1.4.0 code and earlier demonstration materials predate Crypto World's Fair. We disclose this prior development rather than presenting it as work first created during the hackathon.
>
> For this entry, we propose a new settlement application that connects OWP-backed delivery and explicit customer acceptance to an onchain escrow. Research for this application began on October 5, 2026. At this research baseline, the escrow program, wallet integration and onchain settlement flow have not yet been implemented. The final submission will identify the exact new components, their commit history, deployment evidence and tests completed within the contest period.
>
> The application will disclose its verification bridge as a trusted attester and distinguish testnet settlement from real-money payments. Existing OWP verification or acceptance records are not evidence of prior onchain payment, customer adoption, revenue or an independent security audit.

最终填报时还要补：实际依赖 SHA、赛期新增起止提交、每个旧模块来源、实际部署/测试、融资和实际成员信息。提交文案必须删去不再准确的计划时态，不能保留占位项假装完成。

## 6. 当前状态

- 已完成：官方规则研究、现有底座读取、最小产品与新增缺口分析、本地研究文档。
- 进行中：没有合约开发或部署正在后台运行；实施尚未开始。
- 下一步：本届表单与团队确认、固定依赖、工具链与钱包签名/托管原型可行性检查。
- Not evidenced：本届报名/作品提交、合约部署、实际链上结算、真实付费试点、收入、客户采用、第三方安全审计。
