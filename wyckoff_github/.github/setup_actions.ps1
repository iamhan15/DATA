# GitHub Actions 快速配置脚本 (Windows PowerShell)
# 使用 GitHub CLI 自动配置 Tushare Token Secret

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "GitHub Actions 快速配置" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否安装了 gh
try {
    $ghVersion = gh --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "gh not found"
    }
} catch {
    Write-Host "❌ 错误: 未找到 GitHub CLI (gh)" -ForegroundColor Red
    Write-Host ""
    Write-Host "请先安装 GitHub CLI:" -ForegroundColor Yellow
    Write-Host "  winget install GitHub.cli" -ForegroundColor Gray
    Write-Host "  或访问: https://cli.github.com/" -ForegroundColor Gray
    exit 1
}

Write-Host "✅ GitHub CLI 已就绪" -ForegroundColor Green
Write-Host ""

# 检查是否已登录
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  需要先登录 GitHub" -ForegroundColor Yellow
    Write-Host ""
    $loginChoice = Read-Host "是否现在登录? (y/n)"
    if ($loginChoice -eq "y") {
        gh auth login
    } else {
        Write-Host "取消配置" -ForegroundColor Yellow
        exit 0
    }
}

# 获取当前仓库信息
try {
    $repoInfo = gh repo view --json nameWithOwner | ConvertFrom-Json
    $repo = $repoInfo.nameWithOwner
    Write-Host "📦 当前仓库: $repo" -ForegroundColor Green
} catch {
    Write-Host "❌ 无法获取仓库信息，请确认在正确的目录中" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 提示输入 Tushare Token
Write-Host "请输入您的 Tushare Token:" -ForegroundColor Cyan
Write-Host "(从 .env 文件中复制，或从 https://tushare.pro/ 获取)" -ForegroundColor Gray
Write-Host ""
$tushareToken = Read-Host "TUSHARE_TOKEN" -AsSecureString

if ([string]::IsNullOrWhiteSpace($tushareToken)) {
    Write-Host "❌ 错误: Token 不能为空" -ForegroundColor Red
    exit 1
}

# 转换 SecureString 为普通字符串
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($tushareToken)
$plainToken = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

# 确认配置
Write-Host ""
Write-Host "即将配置以下 Secret:" -ForegroundColor Cyan
Write-Host "  仓库: $repo" -ForegroundColor Gray
Write-Host "  名称: TUSHARE_TOKEN" -ForegroundColor Gray
Write-Host "  值: $($plainToken.Substring(0, [Math]::Min(10, $plainToken.Length)))..." -ForegroundColor Gray
Write-Host ""
$confirm = Read-Host "确认配置? (y/n)"

if ($confirm -ne "y") {
    Write-Host "取消配置" -ForegroundColor Yellow
    exit 0
}

# 设置 Secret
Write-Host ""
Write-Host "⚙️  正在配置 Secret..." -ForegroundColor Cyan

$success = $true
try {
    echo $plainToken | gh secret set TUSHARE_TOKEN --repo $repo
} catch {
    $success = $false
}

if ($success) {
    Write-Host ""
    Write-Host "✅ 配置成功!" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步:" -ForegroundColor Cyan
    Write-Host "1. 进入 GitHub 仓库页面" -ForegroundColor Gray
    Write-Host "2. 点击 Actions 标签" -ForegroundColor Gray
    Write-Host "3. 选择 'Tushare Offline Data Fetch' 工作流" -ForegroundColor Gray
    Write-Host "4. 点击 'Run workflow' 进行测试" -ForegroundColor Gray
    Write-Host ""
    Write-Host "或者使用命令触发:" -ForegroundColor Cyan
    Write-Host "  gh workflow run tushare_offline_data.yml --ref main" -ForegroundColor Gray
}
else {
    Write-Host ""
    Write-Host "❌ 配置失败" -ForegroundColor Red
    Write-Host "请手动在 GitHub Web 界面配置:" -ForegroundColor Yellow
    Write-Host "  Settings > Secrets and variables > Actions > New repository secret" -ForegroundColor Gray
    exit 1
}