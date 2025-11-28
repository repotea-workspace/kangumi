#!/bin/bash

# 计费模式切换脚本

set -e

echo "=== ECS实例计费模式切换工具 ==="
echo ""

# 显示当前配置
if [ -f "terraform.tfvars" ]; then
    current_spot_strategy=$(grep "^SPOT_STRATEGY" terraform.tfvars 2>/dev/null | cut -d'"' -f2 || echo "NoSpot")
    echo "当前配置: $current_spot_strategy"
else
    echo "未找到terraform.tfvars文件，请先创建配置文件"
    echo "运行: cp terraform.tfvars.example terraform.tfvars"
    exit 1
fi

echo ""
echo "请选择计费模式："
echo "1) 按量付费模式 (NoSpot) - 稳定但价格较高"
echo "2) 竞价实例模式 (SpotAsPriceGo) - 便宜但可能被回收"
echo "3) 竞价实例限价模式 (SpotWithPriceLimit) - 设置最高价格"
echo "4) 查看当前配置"
echo "0) 退出"
echo ""

read -p "请输入选项 (0-4): " choice

case $choice in
    1)
        echo "切换到按量付费模式..."
        sed -i 's/^SPOT_STRATEGY.*$/SPOT_STRATEGY = "NoSpot"/' terraform.tfvars
        sed -i 's/^# SPOT_STRATEGY.*NoSpot.*/SPOT_STRATEGY = "NoSpot"/' terraform.tfvars
        echo "✓ 已切换到按量付费模式"
        ;;
    2)
        echo "切换到竞价实例模式..."
        sed -i 's/^SPOT_STRATEGY.*$/SPOT_STRATEGY = "SpotAsPriceGo"/' terraform.tfvars
        sed -i 's/^# SPOT_STRATEGY.*NoSpot.*/SPOT_STRATEGY = "SpotAsPriceGo"/' terraform.tfvars
        # 确保SPOT_DURATION被启用
        if ! grep -q "^SPOT_DURATION" terraform.tfvars; then
            echo 'SPOT_DURATION = 1' >> terraform.tfvars
        fi
        echo "✓ 已切换到竞价实例模式"
        echo "注意: 竞价实例价格更低，但可能在资源紧张时被系统回收"
        ;;
    3)
        echo "切换到竞价实例限价模式..."
        sed -i 's/^SPOT_STRATEGY.*$/SPOT_STRATEGY = "SpotWithPriceLimit"/' terraform.tfvars
        sed -i 's/^# SPOT_STRATEGY.*NoSpot.*/SPOT_STRATEGY = "SpotWithPriceLimit"/' terraform.tfvars
        # 确保SPOT_DURATION被启用
        if ! grep -q "^SPOT_DURATION" terraform.tfvars; then
            echo 'SPOT_DURATION = 1' >> terraform.tfvars
        fi
        echo "✓ 已切换到竞价实例限价模式"
        echo "注意: 需要设置最高出价，超过此价格时实例会被回收"
        ;;
    4)
        echo "当前配置信息:"
        echo "==============="
        grep -E "^(SPOT_STRATEGY|SPOT_DURATION)" terraform.tfvars || echo "未找到相关配置"
        ;;
    0)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac

echo ""
echo "配置已更新，当前设置："
grep -E "^(SPOT_STRATEGY|SPOT_DURATION)" terraform.tfvars || echo "未找到相关配置"
echo ""
echo "要应用更改，请运行："
echo "terraform plan"
echo "terraform apply"
