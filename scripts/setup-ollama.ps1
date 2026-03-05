# Ollama 本地模型快速配置脚本
# 此脚本将帮助您快速下载和配置 Ollama 本地模型

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Ollama 本地模型快速配置工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Ollama 是否已安装
Write-Host "检查 Ollama 安装状态..." -ForegroundColor Yellow
try {
    $ollamaVersion = ollama --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Ollama 已安装: $ollamaVersion" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Ollama 未安装" -ForegroundColor Red
    Write-Host ""
    Write-Host "请访问 https://ollama.com 下载并安装 Ollama" -ForegroundColor Yellow
    Write-Host "安装完成后，请重新运行此脚本" -ForegroundColor Yellow
    Read-Host "按任意键退出"
    exit
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  选择要下载的模型" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 聊天模型选择
Write-Host "聊天模型选择：" -ForegroundColor Yellow
Write-Host "1. qwen2.5:7b  (推荐 - 7B参数, 约4GB显存, 性能均衡)"
Write-Host "2. qwen2.5:14b (14B参数, 约8GB显存, 效果更好)"
Write-Host "3. llama3.1:8b (Meta Llama 3.1, 约5GB显存)"
Write-Host "4. deepseek-r1:7b (DeepSeek R1, 约4GB显存)"
Write-Host "5. 跳过聊天模型下载"
Write-Host ""

$chatChoice = Read-Host "请输入选择 (1-5)"

switch ($chatChoice) {
    "1" { $chatModel = "qwen2.5:7b" }
    "2" { $chatModel = "qwen2.5:14b" }
    "3" { $chatModel = "llama3.1:8b" }
    "4" { $chatModel = "deepseek-r1:7b" }
    "5" { $chatModel = $null }
    default { $chatModel = "qwen2.5:7b" }
}

# Embedding 模型选择
Write-Host ""
Write-Host "Embedding 模型选择：" -ForegroundColor Yellow
Write-Host "1. bge-m3 (推荐 - 中英文混合, 1024维)"
Write-Host "2. nomic-embed-text (英文优先, 768维)"
Write-Host "3. 跳过 Embedding 模型下载"
Write-Host ""

$embedChoice = Read-Host "请输入选择 (1-3)"

switch ($embedChoice) {
    "1" { $embedModel = "bge-m3" }
    "2" { $embedModel = "nomic-embed-text" }
    "3" { $embedModel = $null }
    default { $embedModel = "bge-m3" }
}

# 下载模型
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  开始下载模型" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($chatModel) {
    Write-Host "正在下载聊天模型: $chatModel ..." -ForegroundColor Yellow
    Write-Host "这可能需要几分钟时间，请耐心等待..." -ForegroundColor Yellow
    ollama pull $chatModel
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 聊天模型下载完成" -ForegroundColor Green
    } else {
        Write-Host "✗ 聊天模型下载失败" -ForegroundColor Red
    }
}

Write-Host ""

if ($embedModel) {
    Write-Host "正在下载 Embedding 模型: $embedModel ..." -ForegroundColor Yellow
    Write-Host "这可能需要几分钟时间，请耐心等待..." -ForegroundColor Yellow
    ollama pull $embedModel
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Embedding 模型下载完成" -ForegroundColor Green
    } else {
        Write-Host "✗ Embedding 模型下载失败" -ForegroundColor Red
    }
}

# 显示已安装的模型
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  已安装的模型列表" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
ollama list

# 生成配置建议
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  配置建议" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($chatModel) {
    Write-Host "在系统设置中，请配置：" -ForegroundColor Yellow
    Write-Host "  默认对话模型: ollama/$chatModel" -ForegroundColor Cyan
}

if ($embedModel) {
    Write-Host "  Embedding 模型: ollama/$embedModel" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "或者修改配置文件 saves/config/base.yaml：" -ForegroundColor Yellow

$configContent = @"
default_model: ollama/$chatModel
embed_model: ollama/$embedModel
enable_reranker: false
"@

Write-Host $configContent -ForegroundColor Cyan

# 测试模型
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  模型测试" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$testChoice = Read-Host "是否测试聊天模型？(y/n)"

if ($testChoice -eq "y" -or $testChoice -eq "Y") {
    if ($chatModel) {
        Write-Host ""
        Write-Host "正在测试模型 $chatModel ..." -ForegroundColor Yellow
        Write-Host ""
        ollama run $chatModel "你好，请简单介绍一下你自己"
    } else {
        Write-Host "未选择聊天模型，跳过测试" -ForegroundColor Yellow
    }
}

# 检查 Ollama 服务状态
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  服务状态检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -ErrorAction Stop
    Write-Host "✓ Ollama 服务运行正常 (http://localhost:11434)" -ForegroundColor Green
} catch {
    Write-Host "✗ Ollama 服务未运行，请启动 Ollama" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  配置完成！" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步：" -ForegroundColor Yellow
Write-Host "1. 启动项目：按照项目 README 启动服务" -ForegroundColor White
Write-Host "2. 在系统设置中选择刚才配置的模型" -ForegroundColor White
Write-Host "3. 开始使用本地大模型！" -ForegroundColor White
Write-Host ""
Write-Host "更多信息请查看：docs/本地大模型配置指南.md" -ForegroundColor Cyan
Write-Host ""

Read-Host "按任意键退出"
