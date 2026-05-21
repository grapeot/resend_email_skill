# Resend Email Skill

这是一个面向 AI agent 的 Resend 邮件自动化项目：发送邮件、列出 received email、读取正文、导出 Markdown、读取和下载附件。

这个 repo 是 self-contained 的。它不是 Codex 或 Claude Code 的传统打包 skill 格式，而是提供一个普通 Markdown skill contract：`skills/skill_resend_email.md`，再配套 Python package 和 CLI。

## 功能

- 通过 Resend 发送邮件，支持 dry-run 和自定义 header。
- 通过 Resend receiving API 列出收到的邮件。
- 读取收到邮件的 HTML、text、headers 和附件 metadata。
- 把收到的邮件导出成 Markdown，方便 AI agent 阅读。
- 列出并下载收到邮件的附件。
- 默认测试不触网，真实 live/e2e 测试必须显式开启。

## 安装

在 repo 根目录运行：

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
```

也可以让 Codex、Claude Code、OpenCode 或其它 coding agent 直接执行这些命令。

## 配置

复制 `.env.example` 到 `.env`，然后选择一种 credential 模式。

直接写私有 key：

```bash
RESEND_API_KEY=replace-with-your-resend-api-key
RESEND_FROM_EMAIL="Example Sender <no-reply@example.com>"
RESEND_RECEIVING_ADDRESS=anything@example.resend.app
```

或者使用 1Password reference，在 Python 启动前由 `op run` 解析：

```bash
RESEND_API_KEY=op://your-vault/your-item/resend_api_key
op run --env-file=.env -- resend-email doctor config --format json
```

Python package 只读取已经解析好的环境变量，不直接调用 1Password。

## CLI 使用

dry-run 发送：

```bash
resend-email send --to user@example.com --subject "Hello" --body-file body.md --body-format markdown --header "X-Custom: value" --dry-run --format json
```

`--header "Name: Value"` 可以重复使用。Header name 和 value 会被 trim，dry-run JSON payload 会包含解析后的 `headers` object，便于发送前检查。

确认后真实发送：

```bash
resend-email send --to user@example.com --subject "Hello" --body-file body.md --body-format markdown --confirm-send --format json
```

列出收到的邮件：

```bash
resend-email received list --limit 20 --format json
```

读取与导出：

```bash
resend-email received get <email_id> --format json
resend-email received export-md <email_id> --output-dir data/received/markdown --format json
resend-email received export-all-md --limit 20 --output-dir data/received/markdown --format json
```

附件：

```bash
resend-email received attachments list <email_id> --format json
resend-email received attachments download <email_id> <attachment_id> --output-dir data/received/attachments --format json
```

## 安装给 Agent 使用

这个项目使用普通 Markdown skill contract，不是某个 agent 的传统 packaged skill 格式。

1. 把 `skills/skill_resend_email.md` 放到 agent 能发现的地方，通常是全局或 workspace 的 `skills/` 目录。
2. 查看 workspace 根目录里的 `AGENTS.md`、`CLAUDE.md` 或等价说明文件。
3. 如果这些文件指向某个 skill index 或 discovery 文件，就把这个 skill 加到那里。
4. 如果没有 discovery 文件，就在根说明文件里加一句：Resend email 相关任务先读 `skills/skill_resend_email.md`。

示例：

```text
For Resend email sending, received email retrieval, Markdown export, or attachment handling, read skills/skill_resend_email.md and follow its CLI contract.
```

## 测试

默认测试不触网：

```bash
.venv/bin/python -m pytest -v
```

live tests 必须显式开启：

```bash
RESEND_ENABLE_LIVE_TESTS=1 .venv/bin/python -m pytest -v -m live_integration
```

真实发送需要额外设置 `RESEND_LIVE_ALLOW_SEND=1`。端到端 send-to-self 还需要 `RESEND_LIVE_ALLOW_E2E=1` 和 `RESEND_RECEIVING_ADDRESS`。

## 隐私

不要提交 `.env`、API key、私有 1Password path、收到的邮件正文、raw MIME、附件、本地 SQLite 数据库或 token cache。这个 repo 的公开文件只应该包含假例子。
