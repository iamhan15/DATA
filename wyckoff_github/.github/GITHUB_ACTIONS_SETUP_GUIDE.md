# GitHub Actions 配置完整指南

## 📋 配置步骤总览

1. ✅ 工作流文件已创建（`.github/workflows/tushare_offline_data.yml`）
2. ⚠️ 需要配置 Tushare Token Secret
3. ⚠️ 需要确认 Git 推送权限
4. 🎯 测试运行工作流
5. 📊 监控执行结果

---

## 🔧 详细配置步骤

### 步骤 1: 配置 Tushare Token Secret

#### 方法A: 通过 GitHub Web 界面（推荐）

1. **进入仓库设置**
   - 打开您的 GitHub 仓库页面
   - 点击顶部的 **Settings** 标签

2. **找到 Secrets 配置**
   - 在左侧菜单中找到 **Secrets and variables**
   - 点击展开，选择 **Actions**

3. **添加新的 Secret**
   - 点击 **New repository secret** 按钮
   - 填写以下信息：
     ```
     Name: TUSHARE_TOKEN
     Value: 5f11e21cdef4400f3c458621ace3cec7c7b9409dc75ec870e285bf38
     ```
   - 点击 **Add secret** 保存

4. **验证配置**
   - 确认 `TUSHARE_TOKEN` 出现在 Secrets 列表中
   - 值会被隐藏显示为 `••••••••`

#### 方法B: 通过 GitHub CLI（高级用户）

```bash
# 安装 GitHub CLI（如果尚未安装）
# Windows: winget install GitHub.cli
# Mac: brew install gh
# Linux: 参见 https://cli.github.com/

# 登录 GitHub
gh auth login

# 设置 Secret
gh secret set TUSHARE_TOKEN --body "5f11e21cdef4400f3c458621ace3cec7c7b9409dc75ec870e285bf38"
```

---

### 步骤 2: 配置 Git 推送权限

工作流需要将拉取的数据推送到仓库，需要确保有写入权限。

#### 检查点 1: 确认使用 Personal Access Token (PAT)

GitHub Actions 默认使用 `GITHUB_TOKEN`，但有时需要额外的权限。

**如果需要配置 PAT：**

1. **创建 Personal Access Token**
   - 访问: https://github.com/settings/tokens
   - 点击 **Generate new token (classic)**
   - 选择以下权限：
     - ✅ `repo` (完整仓库访问权限)
     - ✅ `workflow` (更新工作流文件)
   - 点击 **Generate token**
   - **重要**: 复制并保存 Token（只显示一次）

2. **添加 PAT 到 Secrets**
   ```
   Name: GH_PAT
   Value: <您刚才生成的 Token>
   ```

3. **修改工作流使用 PAT**（可选）

如果默认的 `GITHUB_TOKEN` 不够用，可以修改工作流：

```yaml
- name: Commit and push data
  env:
    GH_PAT: ${{ secrets.GH_PAT }}
  run: |
    git config --local user.email "action@github.com"
    git config --local user.name "GitHub Action"
    # 使用 PAT 进行推送
    git remote set-url origin https://x-access-token:${GH_PAT}@github.com/${{ github.repository }}.git
    git add data/local_parquet_hist/*.parquet
    git add data/tushare_rate_limit_state.json
    git diff --staged --quiet || git commit -m "Update Tushare offline data [skip ci]"
    git push
  continue-on-error: true
```

#### 检查点 2: 确认分支保护规则

如果您的主分支有保护规则，需要允许 GitHub Actions 推送：

1. 进入 **Settings** > **Branches**
2. 找到分支保护规则
3. 确保勾选了 **Allow force pushes**（如果需要）
4. 确保 **Require status checks to pass before merging** 不会阻止 Actions

---

### 步骤 3: 手动测试工作流

在启用定时任务之前，先手动运行一次测试。

#### 方法 1: 通过 GitHub Web 界面

1. **进入 Actions 标签页**
   - 点击仓库顶部的 **Actions** 标签

2. **选择工作流**
   - 在左侧列表中找到 **Tushare Offline Data Fetch**
   - 点击进入

3. **运行工作流**
   - 点击右上角的 **Run workflow** 按钮
   - 选择分支（通常是 `main` 或 `master`）
   - （可选）配置参数：
     ```
     symbols: 600519,000001  # 留空则拉取所有股票
     days: 30                 # 拉取天数
     force_update: false      # 是否强制更新
     ```
   - 点击 **Run workflow**

4. **监控执行**
   - 点击刚创建的运行记录
   - 查看实时日志输出
   - 等待完成（可能需要几分钟到几小时，取决于拉取的股票数量）

#### 方法 2: 通过 GitHub CLI

```bash
# 触发工作流
gh workflow run tushare_offline_data.yml \
  --ref main \
  -f symbols="600519,000001" \
  -f days=30 \
  -f force_update=false

# 查看运行状态
gh run list --workflow=tushare_offline_data.yml

# 查看详细日志
gh run view <run-id> --log
```

---

### 步骤 4: 验证执行结果

工作流完成后，检查以下内容：

#### 检查点 1: 查看运行日志

1. 进入 **Actions** 标签页
2. 点击最近的运行记录
3. 检查每个步骤的状态：
   - ✅ Checkout code
   - ✅ Set up Python
   - ✅ Install dependencies
   - ✅ Create data directories
   - ✅ Fetch all stocks data / Fetch specific stocks data
   - ✅ Show data summary
   - ✅ Commit and push data（可能显示黄色警告，这是正常的）
   - ✅ Upload data as artifact

#### 检查点 2: 确认数据文件

1. **查看仓库文件**
   - 回到 **Code** 标签页
   - 导航到 `data/local_parquet_hist/` 目录
   - 确认有新的 `.parquet` 文件

2. **查看提交历史**
   - 点击 **Commits**
   - 查找类似 "Update Tushare offline data [skip ci]" 的提交
   - 点击查看变更的文件

3. **下载 Artifact**（可选）
   - 在运行记录页面底部
   - 找到 **Artifacts** 部分
   - 点击 `tushare-offline-data` 下载
   - 解压后查看 Parquet 文件

#### 检查点 3: 验证数据内容

下载一个 Parquet 文件并在本地验证：

```python
import pandas as pd
from pathlib import Path

# 读取下载的 Parquet 文件
df = pd.read_parquet("600519.parquet")

print(f"记录数: {len(df)}")
print(f"列名: {list(df.columns)}")
print(f"日期范围: {df['date'].min()} 至 {df['date'].max()}")
print(df.head())
```

---

### 步骤 5: 配置定时任务（可选）

工作流已经配置了定时任务，每天 UTC 10:00（北京时间 18:00）自动运行。

#### 当前配置

```yaml
on:
  schedule:
    # 每天 UTC 时间 10:00 运行（北京时间 18:00，收盘后）
    - cron: '0 10 * * *'
```

#### 修改运行时间（如需要）

Cron 表达式格式：`分钟 小时 日 月 星期`

**常用时间示例：**

```yaml
# 每天早上 9:00（UTC）/ 下午 17:00（北京）
- cron: '0 9 * * *'

# 每周一早上 8:00（UTC）/ 下午 16:00（北京）
- cron: '0 8 * * 1'

# 每天两次：早上和晚上
- cron: '0 1 * * *'   # UTC 1:00 / 北京 9:00
- cron: '0 10 * * *'  # UTC 10:00 / 北京 18:00

# 工作日每天下午 6 点（北京）
- cron: '0 10 * * 1-5'
```

**注意：**
- GitHub Actions 的定时任务可能有最多 1 小时的延迟
- 频繁运行的定时任务可能会受到限制
- 建议只在交易日的收盘后运行

---

## ⚠️ 注意事项

### 1. API 调用限制

- **每分钟**: 最多 49 次调用（已配置为保守值）
- **每天**: 最多 7999 次调用
- **全市场约 5000 股**: 需要约 100-120 分钟

**建议：**
- 首次运行时只拉取关注的股票
- 确认定时任务的频率不要太高
- 监控 Tushare 账户的积分使用情况

### 2. 存储空间

- GitHub 仓库有 1GB 免费存储限制
- Parquet 文件虽然压缩率高，但全市场数据仍可能较大
- 建议：
  - 定期清理旧数据
  - 只保留关注的股票
  - 考虑使用 Git LFS（如果数据量很大）

### 3. 运行时间限制

- GitHub Actions 免费用户每月 2000 分钟
- 单次运行最长 6 小时
- 全量拉取可能需要较长时间

**优化建议：**
- 使用增量更新（默认已启用）
- 分批拉取大量股票
- 减少不必要的强制更新

### 4. 网络稳定性

- GitHub Actions 运行在云端，网络通常稳定
- 但仍可能出现临时故障
- 工作流已配置 `continue-on-error: true`，单个步骤失败不会中断整个流程

---

## 🐛 故障排除

### 问题 1: Secret 未找到

**错误信息：**
```
Error: Input required and not supplied: TUSHARE_TOKEN
```

**解决方案：**
1. 确认已在 Settings > Secrets > Actions 中添加了 `TUSHARE_TOKEN`
2. 检查名称是否完全匹配（大小写敏感）
3. 重新触发工作流

### 问题 2: Git 推送失败

**错误信息：**
```
remote: Permission to username/repo.git denied to github-actions[bot].
```

**解决方案：**
1. 检查分支保护规则
2. 尝试使用 Personal Access Token（见步骤 2）
3. 确认仓库不是 fork 的（fork 的 Actions 权限有限）

### 问题 3: 依赖安装失败

**错误信息：**
```
ERROR: Could not find a version that satisfies the requirement pandas
```

**解决方案：**
1. 检查工作流中的 Python 版本（目前是 3.11）
2. 尝试更新 pip: `pip install --upgrade pip`
3. 检查网络连接

### 问题 4: 运行超时

**错误信息：**
```
Job was cancelled due to timeout
```

**解决方案：**
1. 减少拉取的股票数量
2. 减少拉取天数
3. 使用增量更新而非强制更新
4. 考虑升级到 GitHub Pro（更长的超时时间）

### 问题 5: 数据文件未生成

**症状：**
- 工作流显示成功
- 但没有新的 Parquet 文件

**检查：**
1. 查看日志中的 "Show data summary" 步骤
2. 确认 Tushare Token 有效且有足够积分
3. 检查股票代码是否正确
4. 查看是否有 API 调用失败的错误信息

---

## 📊 监控和维护

### 定期检查清单

- [ ] 每周检查一次工作流运行状态
- [ ] 每月查看 Tushare 积分使用情况
- [ ] 每季度清理不需要的股票数据
- [ ] 监控 GitHub Actions 使用时长

### 查看使用统计

```bash
# 查看本月 Actions 使用时长
gh api /repos/{owner}/{repo}/actions/usage

# 查看最近的工作流运行
gh run list --limit 10
```

### 清理旧数据

如果需要清理仓库中的旧 Parquet 文件：

```bash
# 本地操作
git rm data/local_parquet_hist/*.parquet
git commit -m "Remove old parquet files"
git push

# 或者只保留特定股票
git rm data/local_parquet_hist/[!6]*.parquet  # 删除非 6 开头的股票
git commit -m "Keep only Shanghai stocks"
git push
```

---

## 🎯 最佳实践

### 1. 首次运行建议

```yaml
# 先测试少量股票
symbols: 600519,000001,300750
days: 30
force_update: false
```

### 2. 日常更新策略

```yaml
# 只更新最新数据
symbols: (留空，更新所有已有股票)
days: 1
force_update: false
```

### 3. 定期全量更新

```yaml
# 每月一次全量更新
symbols: (留空)
days: 365
force_update: true
```

### 4. 监控告警（可选）

可以配置 GitHub Actions 失败时发送通知：

```yaml
- name: Notify on failure
  if: failure()
  uses: actions/github-script@v6
  with:
    script: |
      github.rest.issues.create({
        owner: context.repo.owner,
        repo: context.repo.repo,
        title: 'Tushare Data Fetch Failed',
        body: `Workflow failed: ${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`
      })
```

---

## 📞 获取帮助

如果遇到问题：

1. **查看工作流日志** - 最直接的调试信息
2. **查阅文档** - `.github/TUSHARE_ACTIONS_SETUP.md`
3. **检查 Secret 配置** - 确认 Token 正确
4. **手动测试** - 先在本地运行验证
5. **查看 GitHub Status** - https://www.githubstatus.com/

---

## ✅ 配置完成检查清单

- [ ] TUSHARE_TOKEN 已添加到 Secrets
- [ ] 工作流文件已提交到仓库
- [ ] 手动运行测试成功
- [ ] 数据文件已生成并提交
- [ ] 定时任务已确认配置
- [ ] 了解了如何监控和调试

恭喜！您已成功配置 GitHub Actions 自动更新 Tushare 离线数据。

---

**最后更新**: 2026-04-27  
**版本**: 1.0.0