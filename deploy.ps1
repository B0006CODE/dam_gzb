#!/usr/bin/env pwsh

# Smart Water 项目快速部署脚本 - Windows PowerShell 版本
# 用法: .\deploy.ps1 [start|stop|restart|status|logs|clean|start-prod|stop-prod|restart-prod|status-prod|logs-prod]

param(
    [Parameter(Position=0)]
    [ValidateSet('start', 'stop', 'restart', 'status', 'logs', 'clean', 'start-all', 'start-prod', 'stop-prod', 'restart-prod', 'status-prod', 'logs-prod')]
    [string]$Action = 'start',
    
    [Parameter()]
    [switch]$Help
)

# 颜色输出函数
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = 'White'
    )
    Write-Host $Message -ForegroundColor $Color
}

function Show-Help {
    Write-ColorOutput "`n=== Smart Water 快速部署脚本 ===`n" "Cyan"
    Write-Host "用法: .\deploy.ps1 [命令] [选项]"
    Write-Host "`n可用命令:"
    Write-Host "  start      - 启动基础服务（默认）"
    Write-Host "  start-all  - 启动所有服务（包含 GPU 服务）"
    Write-Host "  start-prod - 启动生产模式服务"
    Write-Host "  stop       - 停止所有服务"
    Write-Host "  stop-prod  - 停止生产模式服务"
    Write-Host "  restart    - 重启所有服务"
    Write-Host "  restart-prod - 重启生产模式服务"
    Write-Host "  status     - 查看服务状态"
    Write-Host "  status-prod - 查看生产模式服务状态"
    Write-Host "  logs       - 查看服务日志"
    Write-Host "  logs-prod  - 查看生产模式服务日志"
    Write-Host "  clean      - 停止并清除所有数据（⚠️ 危险操作）"
    Write-Host "`n示例:"
    Write-Host "  .\deploy.ps1              # 启动基础服务"
    Write-Host "  .\deploy.ps1 start-all    # 启动包含 GPU 的所有服务"
    Write-Host "  .\deploy.ps1 start-prod   # 以生产模式启动服务"
    Write-Host "  .\deploy.ps1 status       # 查看服务状态"
    Write-Host "  .\deploy.ps1 logs         # 查看日志"
    Write-Host ""
}

function Get-ComposeArgs {
    param(
        [bool]$Production = $false,
        [bool]$IncludeGpu = $false
    )

    $args = @("compose")
    if ($Production) {
        $args += @("-f", "docker-compose.yml", "-f", "docker-compose.prod.yml")
    } else {
        $args += @("-f", "docker-compose.yml", "-f", "docker-compose.dev.yml")
    }
    if ($IncludeGpu) {
        $args += @("--profile", "all")
    }
    return $args
}

function Test-Prerequisites {
    Write-ColorOutput "`n🔍 检查系统要求..." "Yellow"
    
    # 检查 Docker
    try {
        $dockerVersion = docker --version
        Write-ColorOutput "✓ Docker: $dockerVersion" "Green"
    } catch {
        Write-ColorOutput "✗ 错误: 未找到 Docker，请先安装 Docker Desktop" "Red"
        Write-Host "  下载地址: https://www.docker.com/products/docker-desktop"
        exit 1
    }
    
    # 检查 Docker Compose
    try {
        $composeVersion = docker compose version
        Write-ColorOutput "✓ Docker Compose: $composeVersion" "Green"
    } catch {
        Write-ColorOutput "✗ 错误: Docker Compose 不可用" "Red"
        exit 1
    }
    
    # 检查 .env 文件
    if (-not (Test-Path ".env")) {
        Write-ColorOutput "`n⚠️  未找到 .env 文件" "Yellow"
        if (Test-Path ".env.template") {
            Write-ColorOutput "是否从 .env.template 创建 .env 文件？[Y/n]" "Yellow"
            $response = Read-Host
            if ($response -eq '' -or $response -eq 'Y' -or $response -eq 'y') {
                Copy-Item ".env.template" ".env"
                Write-ColorOutput "✓ 已创建 .env 文件，请编辑并配置必要的环境变量" "Green"
                Write-ColorOutput "  至少需要配置一个 LLM API Key（如 SILICONFLOW_API_KEY）" "Yellow"
                Write-Host "`n按任意键继续..."
                $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            }
        } else {
            Write-ColorOutput "✗ 错误: 未找到 .env.template 文件" "Red"
            exit 1
        }
    } else {
        Write-ColorOutput "✓ .env 文件存在" "Green"
    }
    
    Write-ColorOutput "✓ 系统要求检查通过`n" "Green"
}

function Start-Services {
    param(
        [bool]$IncludeGpu = $false,
        [bool]$Production = $false
    )
    
    Test-Prerequisites
    
    $composeArgs = Get-ComposeArgs -Production $Production -IncludeGpu $IncludeGpu

    if ($Production) {
        Write-ColorOutput "`n🚀 启动生产模式服务..." "Cyan"
        docker @composeArgs up --build -d
    } elseif ($IncludeGpu) {
        Write-ColorOutput "`n🚀 启动所有服务（包含 GPU 服务）..." "Cyan"
        Write-ColorOutput "⚠️  GPU 服务需要 NVIDIA GPU 和 nvidia-container-toolkit" "Yellow"
        docker @composeArgs up --build -d
    } else {
        Write-ColorOutput "`n🚀 启动基础服务..." "Cyan"
        docker @composeArgs up --build -d
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "`n✓ 服务启动成功！" "Green"
        Write-ColorOutput "`n⏱️  首次启动需要 5-10 分钟来下载镜像和初始化数据库" "Yellow"
        if ($Production) {
            Write-ColorOutput "   请使用 '.\deploy.ps1 status-prod' 检查服务状态`n" "Yellow"
        } else {
            Write-ColorOutput "   请使用 '.\deploy.ps1 status' 检查服务状态`n" "Yellow"
        }
        
        Write-ColorOutput "📋 访问地址:" "Cyan"
        if ($Production) {
            Write-Host "  前端界面:    http://localhost:80"
            Write-Host "  API 健康检查: http://localhost:5050/api/system/health"
        } else {
            Write-Host "  前端界面:    http://localhost:5173"
            Write-Host "  API 文档:    http://localhost:5050/docs"
        }
        Write-Host "  Neo4j 浏览器: http://localhost:7474"
        Write-Host "  MinIO 控制台: http://localhost:9001"
        Write-Host ""
    } else {
        Write-ColorOutput "`n✗ 服务启动失败，请查看日志: .\deploy.ps1 logs" "Red"
        exit 1
    }
}

function Stop-Services {
    param([bool]$Production = $false)

    if ($Production) {
        Write-ColorOutput "`n🛑 停止生产模式服务..." "Yellow"
    } else {
        Write-ColorOutput "`n🛑 停止所有服务..." "Yellow"
    }
    $composeArgs = Get-ComposeArgs -Production $Production
    docker @composeArgs down
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✓ 服务已停止`n" "Green"
    }
}

function Restart-Services {
    param([bool]$Production = $false)

    if ($Production) {
        Write-ColorOutput "`n🔄 重启生产模式服务..." "Yellow"
    } else {
        Write-ColorOutput "`n🔄 重启所有服务..." "Yellow"
    }
    $composeArgs = Get-ComposeArgs -Production $Production
    docker @composeArgs restart
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✓ 服务已重启`n" "Green"
        Show-Status -Production $Production
    }
}

function Show-Status {
    param([bool]$Production = $false)

    Write-ColorOutput "`n📊 服务状态:" "Cyan"
    $composeArgs = Get-ComposeArgs -Production $Production
    docker @composeArgs ps
    
    Write-ColorOutput "`n💾 磁盘使用:" "Cyan"
    docker system df
}

function Show-Logs {
    param([bool]$Production = $false)

    Write-ColorOutput "`n📜 服务日志 (Ctrl+C 退出):" "Cyan"
    $composeArgs = Get-ComposeArgs -Production $Production
    docker @composeArgs logs -f --tail=100
}

function Clean-All {
    Write-ColorOutput "`n⚠️  警告: 这将删除所有容器、网络和数据卷！" "Red"
    Write-ColorOutput "所有数据将被永久删除，是否继续？[y/N]" "Red"
    $response = Read-Host
    
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-ColorOutput "`n🧹 清理所有数据..." "Yellow"
        docker compose down -v
        
        if (Test-Path "docker/volumes") {
            Write-ColorOutput "删除本地数据目录..." "Yellow"
            Remove-Item -Recurse -Force "docker/volumes"
        }
        
        Write-ColorOutput "✓ 清理完成`n" "Green"
    } else {
        Write-ColorOutput "✗ 已取消`n" "Yellow"
    }
}

# 主逻辑
if ($Help) {
    Show-Help
    exit 0
}

switch ($Action) {
    'start' {
        Start-Services -IncludeGpu $false -Production $false
    }
    'start-all' {
        Start-Services -IncludeGpu $true -Production $false
    }
    'start-prod' {
        Start-Services -IncludeGpu $false -Production $true
    }
    'stop' {
        Stop-Services -Production $false
    }
    'stop-prod' {
        Stop-Services -Production $true
    }
    'restart' {
        Restart-Services -Production $false
    }
    'restart-prod' {
        Restart-Services -Production $true
    }
    'status' {
        Show-Status -Production $false
    }
    'status-prod' {
        Show-Status -Production $true
    }
    'logs' {
        Show-Logs -Production $false
    }
    'logs-prod' {
        Show-Logs -Production $true
    }
    'clean' {
        Clean-All
    }
    default {
        Show-Help
    }
}
