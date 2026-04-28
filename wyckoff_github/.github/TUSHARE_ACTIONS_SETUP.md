# GitHub Actions 配置指南

## 配置 Tushare Token

为了使用 GitHub Actions 自动拉取 Tushare 数据，您需要配置 Tushare Token。

### 步骤1: 获取 Tushare Token

1. 访问 [Tushare Pro](https://tushare.pro/)
2. 注册并登录
3. 在个人中心获取您的 Token

### 步骤2: 添加 GitHub Secret

1. 进入您的 GitHub 仓库
2. 点击 **Settings** > **Secrets and variables** > **Actions**
3. 点击 **New repository secret**
4. 创建以下 secret:
   - Name: `TUSHARE_TOKEN`
   - Value: 您的 Tushare Token

### 步骤3: 验证配置

手动触发工作流来验证配置：

1. 进入 **Actions** 标签页
2. 选择 **Tushare Offline Data Fetch** 工作流
3. 点击 **Run workflow**
4. 选择分支并运行

## 工作流说明

### 定时任务

工作流会在每天 UTC 时间 10:00（北京时间 18:00）自动运行，拉取所有A股股票的最新数据。

### 手动触发

您也可以手动触发工作流，支持以下参数：

- **symbols**: 要拉取的股票代码列表（逗号分隔），留空则拉取所有股票
  - 示例: `600519,000001,300750`
  
- **days**: 拉取天数（默认: 365）
  - 示例: `180`
  
- **force_update**: 强制更新（默认: false）
  - 设置为 true 会忽略已有数据，重新拉取

### 使用示例

#### 拉取指定股票
```
symbols: 600519,000001,300750
days: 365
force_update: false
```

#### 强制更新所有股票
```
symbols: (留空)
days: 365
force_update: true
```

## 数据存储

### 本地存储

拉取的数据会保存在:
- `data/local_parquet_hist/*.parquet` - 股票历史数据
- `data/tushare_rate_limit_state.json` - 限流状态

### Git 提交

工作流会自动将新数据提交到仓库（如果启用了此功能）。

注意: 由于 Parquet 文件可能很大，建议在 `.gitignore` 中排除这些数据文件，或者使用 Git LFS。

### Artifact 上传

每次运行都会将数据作为 artifact 上传，保留7天，您可以从 Actions 页面下载。

## 注意事项

1. **API 限制**: 
   - 每分钟最多50次调用
   - 每天最多8000次调用
   - 全市场约5000只股票，全部拉取需要约100分钟

2. **积分要求**:
   - 确保您的 Tushare 账户有足够积分
   - 基础行情接口通常需要一定积分

3. **存储空间**:
   - GitHub 仓库有存储空间限制
   - 建议定期清理旧数据或使用 Git LFS

4. **运行时间**:
   - GitHub Actions 免费用户每月有2000分钟运行时间
   - 全量拉取可能需要较长时间，请合理安排

## 优化建议

1. **只拉取关注的股票**: 使用 `symbols` 参数指定需要监听的股票
2. **减少拉取频率**: 如果不是每天都需要，可以修改 cron 表达式
3. **使用增量更新**: 默认情况下只会更新缺失或过期的数据
4. **监控用量**: 定期检查 Tushare 账户的积分使用情况

## 故障排除

### 问题1: 工作流失败 - Token 无效
```
错误: 未找到 Tushare token
解决: 检查是否正确配置了 TUSHARE_TOKEN secret
```

### 问题2: API 调用失败
```
错误: 获取股票列表失败 / 拉取数据失败
解决: 检查 Tushare 账户积分是否足够，或稍后重试
```

### 问题3: 运行超时
```
错误: Job was cancelled due to timeout
解决: 减少拉取的股票数量或天数，或升级到 GitHub Pro
```

### 问题4: 存储空间不足
```
错误: Repository size limit exceeded
解决: 清理旧的 Parquet 文件，或使用 Git LFS
```

## 自定义工作流

您可以根据需要修改工作流配置文件 `.github/workflows/tushare_offline_data.yml`：

### 修改运行时间
```yaml
on:
  schedule:
    # 每天北京时间 20:00 运行
    - cron: '0 12 * * *'
```

### 修改 Python 版本
```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.10'  # 修改为您需要的版本
```

### 禁用自动提交
注释掉 "Commit and push data" 步骤即可。

## 相关文档

- [Tushare 离线数据拉取模块使用指南](../docs/TUSHARE_OFFLINE_FETCHER_GUIDE.md)
- [GitHub Actions 文档](https://docs.github.com/en/actions)