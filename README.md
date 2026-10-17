# KIP Agent

A desktop AI agent for coding and day-to-day knowledge work — runs locally, acts on real files, and executes commands inside a sandbox.
**Status: active iteration (pre-1.0).** This repository is the team hub for design docs, branches and datasets.

---

## What it is

KIP Agent is a desktop application that puts an LLM agent next to your workspace instead of in a chat tab. It can list and read files in your workspace, write results back, run commands in an isolated container, and keep a verifiable record of what it did.

Design rules we hold ourselves to:

- **Local first** — workspace files stay on the machine; API keys live in the OS keychain, never on disk.
- **Isolation by default when asked** — command execution can be pinned to a fixed container image digest with a read-only root filesystem, no network and a non-root UID.
- **Auditable** — security-sensitive settings require a one-time confirmation and every change is written to an audit log.
- **Model-agnostic** — currently shipping with DeepSeek as the default model; the provider layer is pluggable.

## Who it is for

We serve exactly two tracks.

| Track | User | What they get |
|---|---|---|
| **To C** | Individual developers | A local agent for personal coding tasks: read the repo, run the build, edit files, verify the result. One install, no server. |
| **To B** | Enterprises | Customized agent deployments on top of the same core: private model endpoints, policy-bound command execution, audit trails, and workflows shaped to the customer's own processes. |

We do not do government contracts, agencies, or one-off outsourcing. If the fit is wrong we say so.

## Status

- Pre-1.0. Interfaces, settings keys and internal APIs can change without notice.
- macOS (Apple Silicon) builds are used internally; packages are not code-signed or notarized yet.
- Feature coverage, known gaps and verification logs are tracked in `docs/`.

## This repository

This is a **working repo for the team**, not a stable release channel:

- `main` — shared baseline, kept buildable
- feature branches — one per workstream, pushed here for review
- `docs/` — design notes, verification and build reports
- `data/` — sample datasets used in demos and evaluations

Public on purpose: the docs are readable, forks are welcome, and pull requests are reviewed like any other contribution.

## Contributing

1. Fork, then branch off `main` (`feat/…`, `fix/…`, `docs/…`).
2. Keep commits conventional (`feat:`, `fix:`, `docs:`, `chore:`).
3. Open a pull request with **what changed and how you verified it** — "it works" without a reproduction is not a verification.
4. Never commit API keys, customer data or internal endpoints. Anything security-sensitive goes through the settings pipeline, not into the repo.

## Contact

LuOzawa — linlin700573@gmail.com

---

## 中文

**KIP Agent** 是一款桌面端 AI Agent：装在本机，直接读写你的工作区文件，命令在沙箱容器内执行，做过的每一步都留有审计记录。

- **To C**：面向个人开发者，一个本地 Agent 帮你读仓库、跑构建、改文件、验结果。
- **To B**：面向企业定制，同一套内核之上做私有模型接入、策略化命令执行、审计与流程适配。
- 只做 To C 与 To B 两条线，不做政企单、不做外包、不做一次性项目。

**当前阶段**：pre-1.0，正在快速迭代；接口与配置项可能变动，macOS 包尚未签名公证。

**本仓库**：团队协作仓库，用于推送分支、设计文档与数据。公开是为了让文档可读、允许 fork 与 PR —— 但它是工作仓库，不是稳定发布渠道。

**联系**：linlin700573@gmail.com
