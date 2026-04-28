# GitHub Actions 配置 - 快速开始

## 🎯 目标

配置 GitHub Actions 实现 Tushare 离线数据的自动定时更新。

---

## ⚡ 快速配置（3步完成）

### 方法 1: 使用配置脚本（推荐）

#### Windows 用户

```powershell
# 运行 PowerShell 配置脚本
.\.github\setup_actions.ps1
```

#### Linux/Mac 用户

```bash
# 赋予执行权限
chmod +x .github/setup_actions.sh

# 运行配置脚本
./.github/setup_actions.sh
```

**脚本会自动：**
1. ✅ 检查 GitHub CLI 是否安装
2. ✅ 引导您登录 GitHub
3. ✅ 获取仓库信息
4. ✅ 提示输入 Tushare Token
5. ✅ 自动配置 Secret

---

### 方法 2: 手动配置（Web 界面）

如果您不想使用脚本，可以手动配置：

#### 步骤 1: 添加 Secret

1. 打开 GitHub 仓库页面
2. 点击 **Settings** > **Secrets and variables** > **Actions**
3. 点击 **New repository secret**
4. 填写：
   ```
   Name: TUSHARE_TOKEN
   Value: 5f11e21cdef4400f3c458621ace3cec7c7b9409dc75ec870e285bf38
   ```
5. 点击 **Add secret**

#### 步骤 2: 提交工作流文件

确保以下文件已提交到仓库：
- `.github/workflows/tushare_offline_data.yml`

```bash
git add .github/workflows/tushare_offline_data.yml
git commit -m "Add Tushare offline data fetch workflow"
git push
```

#### 步骤 3: 测试运行

1. 进入 **Actions** 标签页
2. 选择 **Tushare Offline Data Fetch**
3. 点击 **Run workflow**
4. 选择分支并运行

---

## 📋 配置清单

完成以下检查确保配置正确：

- [ ] GitHub CLI 已安装（如果使用脚本）
- [ ] 已登录 GitHub
- [ ] `TUSHARE_TOKEN` Secret 已配置
- [ ] 工作流文件已提交到仓库
- [ ] 手动测试运行成功
- [ ] 数据文件已生成

---

## 🚀 使用工作流

### 手动触发

#### Web 界面
1. 进入 **Actions** > **Tushare Offline Data Fetch**
2. 点击 **Run workflow**
3. （可选）配置参数：
   - `symbols`: 股票代码，如 `600519,000001`（留空则拉取所有）
   - `days`: 拉取天数，默认 365
   - `force_update`: 是否强制更新，默认 false
4. 点击 **Run workflow**

#### 命令行
```bash
# 拉取指定股票
gh workflow run tushare_offline_data.yml \
  --ref main \
  -f symbols="600519,000001" \
  -f days=30

# 拉取所有股票
gh workflow run tushare_offline_data.yml --ref main
```

### 自动定时任务

工作流已配置为每天自动运行：
- **时间**: UTC 10:00（北京时间 18:00）
- **频率**: 每天
- **内容**: 拉取所有A股股票的最新数据

---

## 📊 监控和调试

### 查看运行状态

```bash
# 查看最近的运行
gh run list --workflow=tushare_offline_data.yml

# 查看特定运行的详情
gh run view <run-id>

# 查看实时日志
gh run view <run-id> --log --follow
```

### 常见问题

#### Q1: Secret 未找到
```
Error: Input required and not supplied: TUSHARE_TOKEN
```
**解决**: 确认已在 Settings > Secrets > Actions 中添加了 `TUSHARE_TOKEN`

#### Q2: Git 推送失败
```
remote: Permission denied
```
**解决**: 
- 检查分支保护规则
- 或使用 Personal Access Token

#### Q3: 依赖安装失败
```
ModuleNotFoundError: No module named 'pandas'
```
**解决**: 工作流已包含 `python-dotenv`，应该没问题

---

## 🔧 高级配置

### 修改运行时间

编辑 `.github/workflows/tushare_offline_data.yml`：

```yaml
on:
  schedule:
    # 每天早上 9:00 (UTC) / 下午 17:00 (北京)
    - cron: '0 9 * * *'
```

### 只拉取关注的股票

修改工作流中的默认参数：

```yaml
workflow_dispatch:
  inputs:
    symbols:
      default: '600519,000001,300750'  # 修改为您关注的股票
```

### 禁用自动提交

如果不想将数据提交到仓库，注释掉相关步骤：

```yaml
# - name: Commit and push data
#   run: |
#     ...
```

---

## 📖 详细文档

- **完整配置指南**: [.github/GITHUB_ACTIONS_SETUP_GUIDE.md](GITHUB_ACTIONS_SETUP_GUIDE.md)
- **工作流文件**: [.github/workflows/tushare_offline_data.yml](workflows/tushare_offline_data.yml)
- **模块使用文档**: [docs/TUSHARE_OFFLINE_FETCHER_GUIDE.md](../docs/TUSHARE_OFFLINE_FETCHER_GUIDE.md)

---

## ✅ 下一步

配置完成后：

1. **首次运行**: 手动触发一次，测试配置是否正确
2. **验证数据**: 确认 Parquet 文件已生成
3. **监控运行**: 定期检查工作流执行状态
4. **调整策略**: 根据需求调整拉取频率和范围

---

**祝您使用愉快！** 🎉