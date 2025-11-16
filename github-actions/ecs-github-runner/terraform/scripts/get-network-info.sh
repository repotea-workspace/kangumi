#!/bin/bash

# 获取阿里云资源ID的帮助脚本
# 由于权限限制，此脚本只提供获取ID的方法说明

echo "=== 获取阿里云资源ID指南 ==="
echo ""

# 从.env读取区域
if [ -f ".env" ]; then
    source .env
fi
REGION=${ALI_REGION:-"cn-shenzhen"}

echo "当前区域: $REGION"
echo ""

echo "由于权限限制，需要手动获取以下资源ID："
echo ""

echo "1. VPC ID"
echo "   - 控制台路径: VPC -> 专有网络"
echo "   - CLI命令: aliyun ecs DescribeVpcs --region $REGION"
echo ""

echo "2. VSwitch ID"
echo "   - 控制台路径: VPC -> 交换机"
echo "   - CLI命令: aliyun ecs DescribeVSwitches --region $REGION"
echo ""

echo "3. 安全组ID"
echo "   - 控制台路径: ECS -> 安全组"
echo "   - CLI命令: aliyun ecs DescribeSecurityGroups --region $REGION"
echo ""

echo "4. 镜像ID (Ubuntu 20.04)"
echo "   - 控制台路径: ECS -> 镜像 -> 公共镜像"
echo "   - CLI命令: aliyun ecs DescribeImages --region $REGION --ImageOwnerAlias system --ImageName \"*ubuntu_20_04*\""
echo ""

echo "5. 可用区"
echo "   - 必须与VSwitch所在区域一致"
echo "   - CLI命令: aliyun ecs DescribeZones --region $REGION"
echo ""

echo "获取到ID后，请编辑terraform.tfvars文件："
echo ""
echo "VPC_ID = \"vpc-xxxxxxxxx\""
echo "VSWITCH_ID = \"vsw-xxxxxxxxx\""
echo "AVAILABILITY_ZONE = \"$REGION-a\""
echo "SECURITY_GROUP_ID = \"sg-xxxxxxxxx\""
echo "IMAGE_ID = \"ubuntu_20_04_x64_20G_alibase_xxxxxxxx.vhd\""

echo ""
echo "=== 如果有aliyun CLI权限，可以尝试执行 ==="
if command -v aliyun &> /dev/null; then
    echo "检测到aliyun CLI工具"
    echo ""

    echo "获取VPC:"
    aliyun ecs DescribeVpcs --region $REGION 2>/dev/null || echo "权限不足"
    echo ""

    echo "获取VSwitch:"
    aliyun ecs DescribeVSwitches --region $REGION 2>/dev/null || echo "权限不足"
    echo ""

    echo "获取安全组:"
    aliyun ecs DescribeSecurityGroups --region $REGION 2>/dev/null || echo "权限不足"
    echo ""

    echo "获取Ubuntu镜像:"
    aliyun ecs DescribeImages --region $REGION --ImageOwnerAlias system --ImageName "*ubuntu_20_04*" 2>/dev/null || echo "权限不足"
else
    echo "未检测到aliyun CLI工具"
    echo "请使用阿里云控制台获取ID"
fi
