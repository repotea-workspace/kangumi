#!/bin/bash

# 清理和重新部署脚本

set -e

echo "=== 清理之前的错误状态 ==="

# 清理terraform状态
echo "清理terraform状态文件..."
rm -f terraform.tfstate terraform.tfstate.backup

# 清理计划文件
echo "清理计划文件..."
rm -f plan.out

echo ""
echo "=== 重新初始化和部署 ==="

# 重新初始化
echo "重新初始化terraform..."
terraform init

# 验证配置
echo "验证terraform配置..."
terraform validate

# 生成计划
echo "生成部署计划..."
terraform plan -out=plan.out

echo ""
echo "=== 部署准备完成 ==="
echo "如果计划看起来正确，请运行以下命令来应用："
echo "terraform apply plan.out"
echo ""
echo "或者直接运行："
echo "terraform apply"
