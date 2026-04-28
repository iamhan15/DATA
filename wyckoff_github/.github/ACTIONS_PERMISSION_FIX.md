# GitHub Actions 权限配置指南

## 🔒 问题说明

您的仓库 `iamhan15/DATA` 设置了严格的安全策略：
> "All actions must be from a repository owned by iamhan15"

这意味着只能使用来自 `iamhan15` 账户的 Actions。

---

## ✅ 解决方案（二选一）

### 方案 A: 修改仓库设置（最简单，推荐）

如果您有仓库管理员权限：

#### 步骤 1: 进入 Actions 设置

1. 访问: https://github.com/iamhan15/DATA/settings/actions
2. 或从仓库页面: **Settings** > **Actions** > **General**

#### 步骤 2: 修改权限

找到 **Actions permissions** 部分，选择：

**选项 1: 允许所有 Actions（最简单）**
```
✅ Allow all actions and reusable workflows
```

**选项 2: 允许 GitHub 官方 + 选定的第三方**
```
✅ Allow actions created by GitHub, and select third-party actions
```
然后添加以下 Actions：
- `actions/checkout`
- `actions/setup-python`
- `actions/upload-artifact`

#### 步骤 3: 保存并测试

保存设置后，重新触发工作流即可。

---

### 方案 B: Fork Actions 到自己的仓库

如果无法修改仓库设置，需要 Fork 官方 Actions。

#### 步骤 1: Fork 三个必需的 Actions

在浏览器中依次访问并 Fork：

1. **Checkout Action**
   ```
   访问: https://github.com/actions/checkout
   点击右上角 "Fork" 按钮
   Fork 到您的账户: iamhan15/checkout
   ```

2. **Setup Python Action**
   ```
   访问: https://github.com/actions/setup-python
   点击右上角 "Fork" 按钮
   Fork 到您的账户: iamhan15/setup-python
   ```

3. **Upload Artifact Action**
   ```
   访问: https://github.com/actions/upload-artifact
   点击右上角 "Fork" 按钮
   Fork 到您的账户: iamhan15/upload-artifact
   ```

#### 步骤 2: 确认 Fork 成功

检查以下仓库是否存在：
- ✅ https://github.com/iamhan15/checkout
- ✅ https://github.com/iamhan15/setup-python
- ✅ https://github.com/iamhan15/upload-artifact

#### 步骤 3: 工作流已自动更新

工作流文件 `.github/workflows/tushare_offline_data.yml` 已经更新为使用您的 Fork：

```yaml
- name: Checkout code
  uses: iamhan15/checkout@v4

- name: Set up Python
  uses: iamhan15/setup-python@v5

- name: Upload data as artifact
  uses: iamhan15/upload-artifact@v4
```

#### 步骤 4: 提交并推送

```bash
git add .github/workflows/tushare_offline_data.yml
git commit -m "Update workflow to use forked actions"
git push
```

---

## 📋 验证配置

### 方法 1: 手动触发测试

1. 进入 **Actions** 标签页
2. 选择 **Tushare Offline Data Fetch**
3. 点击 **Run workflow**
4. 观察运行状态

### 方法 2: 查看工作流日志

如果看到类似以下错误，说明配置还有问题：
```
The action 'xxx' is not allowed
```

如果看到：
```
✅ Run actions/checkout@v4
✅ Run actions/setup-python@v5
```
说明配置成功！

---

## 🔧 常见问题

### Q1: Fork 后仍然报错？

**可能原因：**
- Fork 不完整
- 版本标签不存在

**解决方法：**
1. 确认 Fork 的仓库包含所需的 tag（如 v4, v5）
2. 尝试使用具体的 commit SHA 而非 tag：
   ```yaml
   uses: iamhan15/checkout@<commit-sha>
   ```

### Q2: 能否混合使用？

可以！您可以：
- Fork 部分 Actions
- 修改设置允许其他 Actions

### Q3: Fork 后需要维护吗？

**不需要频繁维护**，但建议：
- 定期同步上游更新（可选）
- 关注安全公告

**同步上游更新：**
```bash
cd checkout
git remote add upstream https://github.com/actions/checkout.git
git fetch upstream
git merge upstream/v4
git push origin v4
```

---

## 💡 最佳实践建议

### 推荐：方案 A（修改设置）

**优点：**
- ✅ 简单快速
- ✅ 无需维护 Fork
- ✅ 自动获得最新功能和修复
- ✅ 可以使用任何官方 Actions

**缺点：**
- ⚠️ 需要管理员权限
- ⚠️ 安全性略低（但 GitHub 官方 Actions 很安全）

### 备选：方案 B（Fork Actions）

**优点：**
- ✅ 完全控制
- ✅ 最高安全性
- ✅ 可以自定义修改

**缺点：**
- ❌ 需要手动维护
- ❌ 可能错过安全更新
- ❌ 配置复杂

---

## 🎯 下一步行动

### 如果您选择方案 A：

1. 进入仓库设置修改 Actions 权限
2. 保存后重新触发工作流
3. 完成！✅

### 如果您选择方案 B：

1. Fork 三个 Actions 仓库
2. 工作流文件已更新，直接提交
3. 重新触发工作流测试
4. 完成！✅

---

## 📞 需要帮助？

如果遇到问题：

1. **检查 Fork 是否成功**
   - 访问 `https://github.com/iamhan15/checkout`
   - 确认仓库存在且有内容

2. **查看工作流日志**
   - 进入 Actions 标签页
   - 查看失败的具体步骤
   - 复制错误信息

3. **验证 YAML 语法**
   ```bash
   # 使用在线工具验证
   # https://www.yamllint.com/
   ```

---

## ✅ 配置完成检查清单

- [ ] 选择了方案 A 或方案 B
- [ ] 方案 A: 已修改仓库设置
- [ ] 方案 B: 已 Fork 三个 Actions
- [ ] 工作流文件已更新（方案 B）
- [ ] 代码已提交并推送
- [ ] 手动测试工作流成功
- [ ] 没有权限相关错误

---

**祝您配置顺利！** 🎉