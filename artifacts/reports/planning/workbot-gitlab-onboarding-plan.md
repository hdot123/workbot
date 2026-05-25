# workbot GitLab CE 接入操作清单

> 日期: 2026-05-07
> 状态: 本地准备完成，等待人工执行远程步骤
> 前置: P0-1 GitHub push gate 已封堵，P0-2 GitLab 基础设施已确认

---

## 1. 当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| GitLab CE 实例 | **READY** | `http://node-15.tail5e888.ts.net`，HTTP 302，API 可达 |
| gateway-admin CI | **READY** | 6-stage pipeline 已跑通 |
| gitlab-ci-standards | **READY** | v1.0.0 tagged，6 个模板 |
| workbot `.gitlab-ci.yml` | **LOCAL DRAFT** | 已创建，未推送 |
| workbot GitLab remote | **NOT EXISTS** | 未添加 |
| workbot pipeline | **NOT EXISTS** | 未接入 |

---

## 2. 需要人工确认的信息

| # | 信息 | 建议值 | 说明 |
|---|------|--------|------|
| 1 | GitLab project namespace | `root/workbot` 或 `infra/workbot` | 需确认放在哪个 group/namespace |
| 2 | GitLab remote URL | `http://node-15.tail5e888.ts.net/{namespace}/workbot.git` | 确认后添加 |
| 3 | Runner 策略 | 复用 shared runner | gateway-admin 使用 shared runner，tag: `shell` |
| 4 | Runner tag | `shell` | 与 gitlab-ci-standards 模板一致 |
| 5 | Project access token | 需要创建 | 用于 CI 推送（如果需要） |
| 6 | Visibility | private | workbot 是私有项目 |

---

## 3. 最小接入步骤

### Step 1: 在 GitLab CE 创建 workbot 项目

```
1. 登录 http://node-15.tail5e888.ts.net
2. New Project -> Create blank project
3. Project name: workbot
4. Namespace: root (或 infra)
5. Visibility: Private
6. Initialize with README: NO (已有仓库)
7. 记录项目 URL
```

### Step 2: 添加 GitLab remote

```bash
cd /Users/busiji/workbot
git remote add gitlab http://node-15.tail5e888.ts.net/{namespace}/workbot.git
```

### Step 3: 首次推送到 GitLab

```bash
# 推送当前分支到 GitLab
git push gitlab branch-2-youzy-clone:main
# 或推送 branch-1
git push gitlab branch-1:main
```

### Step 4: 验证 pipeline

```
1. 在 GitLab UI 打开 workbot 项目
2. 进入 CI/CD -> Pipelines
3. 确认 pipeline 自动触发
4. 等待所有 job 完成
5. 确认: secret-scan-workbot PASS
6. 确认: webhook-ingress-pytest PASS (34 tests)
7. 确认: yaml-baseline-parse PASS
8. 确认: github-push-gate-dry-run PASS
```

### Step 5: 失败处理

如果 pipeline 失败：
1. 查看失败 job 日志
2. 本地修复
3. commit + push 到 GitLab
4. 重新验证

---

## 4. 明确禁止

| # | 禁止项 | 原因 |
|---|--------|------|
| 1 | 不推 GitHub | gate-check 绝对 fail-closed，无 GitLab CI evidence |
| 2 | 不绕过 GitLab CI | 所有代码变更必须通过 CI |
| 3 | 不在报告写 secret | 0 findings |
| 4 | 不启用真实 Factory dispatch | 需要 GitLab CI 门禁 ready |
| 5 | 不改 Linear 状态/标签 | 仅允许 commentCreate |
| 6 | 不添加生产部署 job | 仅 lint/test/security/validate/dry-run |

---

## 5. 回滚方案

如果接入失败或需要撤回：

```bash
# 1. 删除 GitLab remote
git remote remove gitlab

# 2. 删除本地 .gitlab-ci.yml 草案
rm .gitlab-ci.yml

# 3. 保持 GitHub push gate fail-closed（无需改动）

# 4. 如需删除 GitLab 项目，在 GitLab UI 操作
```

回滚不影响 GitHub remote 或 P0-1 封堵。

---

*接入操作清单结束*
