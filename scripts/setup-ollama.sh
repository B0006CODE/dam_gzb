#!/bin/bash

# Ollama 本地模型快速配置脚本
# 此脚本将帮助您快速下载和配置 Ollama 本地模型

# 颜色定义
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Ollama 本地模型快速配置工具${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 检查 Ollama 是否已安装
echo -e "${YELLOW}检查 Ollama 安装状态...${NC}"
if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>&1)
    echo -e "${GREEN}✓ Ollama 已安装: $OLLAMA_VERSION${NC}"
else
    echo -e "${RED}✗ Ollama 未安装${NC}"
    echo ""
    echo -e "${YELLOW}正在安装 Ollama...${NC}"
    curl -fsSL https://ollama.com/install.sh | sh
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Ollama 安装成功${NC}"
    else
        echo -e "${RED}✗ Ollama 安装失败${NC}"
        echo -e "${YELLOW}请手动访问 https://ollama.com 下载并安装${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  选择要下载的模型${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 聊天模型选择
echo -e "${YELLOW}聊天模型选择：${NC}"
echo "1. qwen2.5:7b  (推荐 - 7B参数, 约4GB显存, 性能均衡)"
echo "2. qwen2.5:14b (14B参数, 约8GB显存, 效果更好)"
echo "3. llama3.1:8b (Meta Llama 3.1, 约5GB显存)"
echo "4. deepseek-r1:7b (DeepSeek R1, 约4GB显存)"
echo "5. 跳过聊天模型下载"
echo ""

read -p "请输入选择 (1-5): " chat_choice

case $chat_choice in
    1) chat_model="qwen2.5:7b" ;;
    2) chat_model="qwen2.5:14b" ;;
    3) chat_model="llama3.1:8b" ;;
    4) chat_model="deepseek-r1:7b" ;;
    5) chat_model="" ;;
    *) chat_model="qwen2.5:7b" ;;
esac

# Embedding 模型选择
echo ""
echo -e "${YELLOW}Embedding 模型选择：${NC}"
echo "1. bge-m3 (推荐 - 中英文混合, 1024维)"
echo "2. nomic-embed-text (英文优先, 768维)"
echo "3. 跳过 Embedding 模型下载"
echo ""

read -p "请输入选择 (1-3): " embed_choice

case $embed_choice in
    1) embed_model="bge-m3" ;;
    2) embed_model="nomic-embed-text" ;;
    3) embed_model="" ;;
    *) embed_model="bge-m3" ;;
esac

# 下载模型
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  开始下载模型${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

if [ ! -z "$chat_model" ]; then
    echo -e "${YELLOW}正在下载聊天模型: $chat_model ...${NC}"
    echo -e "${YELLOW}这可能需要几分钟时间，请耐心等待...${NC}"
    ollama pull $chat_model
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 聊天模型下载完成${NC}"
    else
        echo -e "${RED}✗ 聊天模型下载失败${NC}"
    fi
fi

echo ""

if [ ! -z "$embed_model" ]; then
    echo -e "${YELLOW}正在下载 Embedding 模型: $embed_model ...${NC}"
    echo -e "${YELLOW}这可能需要几分钟时间，请耐心等待...${NC}"
    ollama pull $embed_model
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Embedding 模型下载完成${NC}"
    else
        echo -e "${RED}✗ Embedding 模型下载失败${NC}"
    fi
fi

# 显示已安装的模型
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  已安装的模型列表${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
ollama list

# 生成配置建议
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  配置建议${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

if [ ! -z "$chat_model" ]; then
    echo -e "${YELLOW}在系统设置中，请配置：${NC}"
    echo -e "${CYAN}  默认对话模型: ollama/$chat_model${NC}"
fi

if [ ! -z "$embed_model" ]; then
    echo -e "${CYAN}  Embedding 模型: ollama/$embed_model${NC}"
fi

echo ""
echo -e "${YELLOW}或者修改配置文件 saves/config/base.yaml：${NC}"

cat << EOF
${CYAN}default_model: ollama/$chat_model
embed_model: ollama/$embed_model
enable_reranker: false${NC}
EOF

# 测试模型
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  模型测试${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

read -p "是否测试聊天模型？(y/n): " test_choice

if [[ $test_choice == "y" || $test_choice == "Y" ]]; then
    if [ ! -z "$chat_model" ]; then
        echo ""
        echo -e "${YELLOW}正在测试模型 $chat_model ...${NC}"
        echo ""
        ollama run $chat_model "你好，请简单介绍一下你自己"
    else
        echo -e "${YELLOW}未选择聊天模型，跳过测试${NC}"
    fi
fi

# 检查 Ollama 服务状态
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  服务状态检查${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama 服务运行正常 (http://localhost:11434)${NC}"
else
    echo -e "${RED}✗ Ollama 服务未运行，请启动 Ollama${NC}"
    echo -e "${YELLOW}提示：运行 'ollama serve' 启动服务${NC}"
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  配置完成！${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${YELLOW}下一步：${NC}"
echo -e "${WHITE}1. 启动项目：按照项目 README 启动服务${NC}"
echo -e "${WHITE}2. 在系统设置中选择刚才配置的模型${NC}"
echo -e "${WHITE}3. 开始使用本地大模型！${NC}"
echo ""
echo -e "${CYAN}更多信息请查看：docs/本地大模型配置指南.md${NC}"
echo ""
