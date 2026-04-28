# GitHub Actions 故障诊断清单

## 📋 请检查以下项目

### 1. Fork 的 Actions 是否存在？

请在浏览器中访问以下链接，确认每个仓库都存在且可访问：

- [ ] https://github.com/iamhan15/checkout
- [ ] https://github.com/iamhan15/setup-python  
- [ ] https://github.com/iamhan15/upload-artifact

**如果任何一个链接显示 404，说明还没有 Fork！**

**解决方法：**
- 选项 A: 修改仓库设置允许所有 Actions（推荐）
- 选项 B: 立即 Fork 缺失的仓库

---

### 2. Secret 是否已配置？

检查 `TUSHARE_TOKEN` 是否正确配置：

1. 访问: https://github.com/iamhan15/DATA/settings/secrets/actions
2. 确认看到 `TUSHARE_TOKEN`
3. 确认值不为空

**如果没有配置：**
```
Name: TUSHARE_TOKEN
Value: 5f11e21cdef4400f3c458621ace3cec7c7b9409dc75ec870e285bf38
```

---

### 3. 查看具体错误信息

请提供以下信息：

#### A. 哪个步骤失败了？
- [ ] Checkout code
- [ ] Set up Python
- [ ] Install dependencies
- [ ] Create data directories
- [ ] Fetch all stocks data / Fetch specific stocks data
- [ ] Show data summary
- [ ] Commit and push data
- [ ] Upload data as artifact

#### B. 错误日志内容

请复制失败步骤的完整日志，特别是：
- 错误消息
- 堆栈跟踪
- 退出码前后的输出

#### C. 工作流运行链接

提供失败运行的 URL，例如：
```
https://github.com/iamhan15/DATA/actions/runs/XXXXX
```

---

## 🔧 快速修复方案

### 方案 1: 修改仓库设置（最简单）⭐

如果您有管理员权限：

1. **访问设置页面**
   ```
   https://github.com/iamhan15/DATA/settings/actions
   ```

2. **修改 Actions 权限**
   - 找到 "Actions permissions"
   - 选择: **Allow all actions and reusable workflows**
   - 点击 Save

3. **重新触发工作流**
   - 进入 Actions 标签页
   - 点击 "Run workflow"

**这是最快的解决方案！**

---

### 方案 2: 确保 Fork 正确

如果必须使用 Fork 的 Actions：

#### 步骤 1: Fork 所有必需的 Actions

在浏览器中依次访问并 Fork：

1. https://github.com/actions/checkout → Fork to iamhan15/checkout
2. https://github.com/actions/setup-python → Fork to iamhan15/setup-python
3. https://github.com/actions/upload-artifact → Fork to iamhan15/upload-artifact

#### 步骤 2: 验证 Fork 成功

确认以下仓库存在且有内容：
- ✅ https://github.com/iamhan15/checkout
- ✅ https://github.com/iamhan15/setup-python
- ✅ https://github.com/iamhan15/upload-artifact

#### 步骤 3: 检查工作流文件

确认 `.github/workflows/tushare_offline_data.yml` 中使用的是：
```yaml
uses: iamhan15/checkout@v4
uses: iamhan15/setup-python@v5
uses: iamhan15/upload-artifact@v4
```

#### 步骤 4: 提交并重新运行

```bash
git add .github/workflows/tushare_offline_data.yml
git commit -m "Fix actions references"
git push
```

---

### 方案 3: 临时简化测试

如果问题持续，可以创建一个简化的测试工作流：

创建文件: `.github/workflows/test_actions.yml`

```yaml
name: Test Actions

on:
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - name: Test checkout
      uses: iamhan15/checkout@v4
    
    - name: Test python setup
      uses: iamhan15/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Test simple command
      run: |
        python --version
        echo "Actions work!"
```

运行这个测试工作流，看是否能成功。

---

## 📊 常见错误及解决

### 错误 1: "The action is not allowed"

**原因:** 仓库设置限制了 Actions 来源

**解决:** 
- 方案 A: 修改仓库设置允许所有 Actions
- 方案 B: 确保已正确 Fork

### 错误 2: "Repository not found"

**原因:** Fork 的仓库不存在或不可访问

**解决:**
- 确认 Fork 成功
- 检查仓库可见性（应该是 public）

### 错误 3: "Input required and not supplied: TUSHARE_TOKEN"

**原因:** Secret 未配置

**解决:**
- 添加 TUSHARE_TOKEN Secret

### 错误 4: "ModuleNotFoundError: No module named 'xxx'"

**原因:** Python 依赖安装失败

**解决:**
- 查看 "Install dependencies" 步骤日志
- 检查网络连接
- 尝试更新 pip

---

## 🎯 下一步行动

请按以下顺序操作：

1. **首先尝试方案 1**（修改仓库设置）- 最简单
2. **如果不行，提供详细错误日志** - 我可以帮您精准诊断
3. **最后考虑方案 2**（Fork Actions）- 最复杂

---

## 📞 需要帮助？

请提供：
1. ✅ 失败的步骤名称
2. ✅ 完整的错误日志（至少最后 20 行）
3. ✅ 工作流运行链接
4. ✅ 您选择的方案（A 还是 B）

我会根据具体错误给出针对性的解决方案！