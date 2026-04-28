#!/bin/bash
# GitHub Actions 快速配置脚本
# 使用 GitHub CLI 自动配置 Tushare Token Secret

set -e

echo "=========================================="
echo "GitHub Actions 快速配置"
echo "=========================================="
echo ""

# 检查是否安装了 gh
if ! command -v gh &> /dev/null; then
    echo "❌ 错误: 未找到 GitHub CLI (gh)"
    echo ""
    echo "请先安装 GitHub CLI:"
    echo "  Windows: winget install GitHub.cli"
    echo "  Mac: brew install gh"
    echo "  Linux: https://cli.github.com/"
    exit 1
fi

# 检查是否已登录
if ! gh auth status &> /dev/null; then
    echo "⚠️  需要先登录 GitHub"
    echo ""
    read -p "是否现在登录? (y/n): " login_choice
    if [ "$login_choice" = "y" ]; then
        gh auth login
    else
        echo "取消配置"
        exit 0
    fi
fi

echo "✅ GitHub CLI 已就绪"
echo ""

# 获取当前仓库信息
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "📦 当前仓库: $REPO"
echo ""

# 提示输入 Tushare Token
echo "请输入您的 Tushare Token:"
echo "(从 .env 文件中复制，或从 https://tushare.pro/ 获取)"
echo ""
read -p "TUSHARE_TOKEN: " tushare_token

if [ -z "$tushare_token" ]; then
    echo "❌ 错误: Token 不能为空"
    exit 1
fi

# 确认配置
echo ""
echo "即将配置以下 Secret:"
echo "  仓库: $REPO"
echo "  名称: TUSHARE_TOKEN"
echo "  值: ${tushare_token:0:10}..."
echo ""
read -p "确认配置? (y/n): " confirm

if [ "$confirm" != "y" ]; then
    echo "取消配置"
    exit 0
fi

# 设置 Secret
echo ""
echo "⚙️  正在配置 Secret..."
gh secret set TUSHARE_TOKEN --body "$tushare_token" --repo "$REPO"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 配置成功!"
    echo ""
    echo "下一步:"
    echo "1. 进入 GitHub 仓库页面"
    echo "2. 点击 Actions 标签"
    echo "3. 选择 'Tushare Offline Data Fetch' 工作流"
    echo "4. 点击 'Run workflow' 进行测试"
    echo ""
    echo "或者使用命令触发:"
    echo "  gh workflow run tushare_offline_data.yml --ref main"
else
    echo ""
    echo "❌ 配置失败"
    echo "请手动在 GitHub Web 界面配置:"
    echo "  Settings > Secrets and variables > Actions > New repository secret"
    exit 1
fi