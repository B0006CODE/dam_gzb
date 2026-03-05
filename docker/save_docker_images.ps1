# PowerShell脚本 - Smart Water 内网部署镜像打包工具
# 用法: .\docker\save_docker_images.ps1
# 功能: 构建并导出所有 Docker 镜像，用于内网离线部署

param(
    [switch]$IncludeGpu,      # 是否包含 GPU 服务镜像
    [switch]$SkipBuild,       # 跳过构建，只导出已有镜像
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Smart Water 内网部署镜像打包工具

用法: .\docker\save_docker_images.ps1 [选项]

选项:
  -IncludeGpu    包含 GPU 服务镜像（mineru, paddlex）
  -SkipBuild     跳过构建步骤，只导出已有镜像
  -Help          显示帮助信息

示例:
  .\docker\save_docker_images.ps1              # 构建并导出基础服务镜像
  .\docker\save_docker_images.ps1 -IncludeGpu  # 包含 GPU 服务
  .\docker\save_docker_images.ps1 -SkipBuild   # 只导出已构建的镜像
"@
    exit 0
}

# 创建输出目录
$OutputDir = "docker_images_backup"
if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$DateTime = Get-Date -Format "yyyyMMdd_HHmm"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Smart Water 内网部署镜像打包工具" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ============================================================
# 步骤 1: 拉取基础镜像
# ============================================================
Write-Host "[1/4] 拉取基础镜像..." -ForegroundColor Yellow

$BaseImages = @(
    # API 服务依赖
    "python:3.12-slim",
    "ghcr.io/astral-sh/uv:0.7.2",
    # Web 服务依赖
    "node:20-alpine",
    "nginx:alpine",
    # 第三方服务
    "neo4j:5.26",
    "quay.io/coreos/etcd:v3.5.5",
    "minio/minio:RELEASE.2023-03-20T20-16-18Z",
    "milvusdb/milvus:v2.5.6"
)

# GPU 服务镜像（可选）
$GpuImages = @(
    "lmsysorg/sglang:v0.4.9.post3-cu126"
    # PaddleX 镜像需要从百度云拉取，这里不自动处理
)

foreach ($Image in $BaseImages) {
    Write-Host "  拉取: $Image" -ForegroundColor Gray
    docker pull $Image 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ $Image" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $Image 拉取失败，尝试使用镜像加速..." -ForegroundColor Red
        # 尝试使用 DaoCloud 镜像加速
        $MirrorImage = "m.daocloud.io/$Image"
        docker pull $MirrorImage
        if ($LASTEXITCODE -eq 0) {
            docker tag $MirrorImage $Image
            docker rmi $MirrorImage
            Write-Host "  ✓ $Image (via mirror)" -ForegroundColor Green
        }
    }
}

if ($IncludeGpu) {
    Write-Host "`n  拉取 GPU 服务镜像（较大，请耐心等待）..." -ForegroundColor Yellow
    foreach ($Image in $GpuImages) {
        Write-Host "  拉取: $Image" -ForegroundColor Gray
        docker pull $Image
    }
}

# ============================================================
# 步骤 2: 构建自定义镜像
# ============================================================
if (-not $SkipBuild) {
    Write-Host "`n[2/4] 构建自定义镜像..." -ForegroundColor Yellow
    
    Write-Host "  构建 API 服务镜像..." -ForegroundColor Gray
    docker compose build api
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ smart-water-api:1.0.0" -ForegroundColor Green
    } else {
        Write-Host "  ✗ API 镜像构建失败" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  构建 Web 服务镜像..." -ForegroundColor Gray
    docker compose build web
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ smart-water-web:1.0.0" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Web 镜像构建失败" -ForegroundColor Red
        exit 1
    }
    
    if ($IncludeGpu) {
        Write-Host "  构建 MinerU 服务镜像..." -ForegroundColor Gray
        docker compose build mineru
        Write-Host "  构建 PaddleX 服务镜像..." -ForegroundColor Gray
        docker compose build paddlex
    }
} else {
    Write-Host "`n[2/4] 跳过构建步骤" -ForegroundColor Gray
}

# ============================================================
# 步骤 3: 导出镜像
# ============================================================
Write-Host "`n[3/4] 导出镜像到 tar 文件..." -ForegroundColor Yellow

# 基础服务镜像列表
$ExportImages = @(
    # 自定义构建的镜像
    "smart-water-api:1.0.0",
    "smart-water-web:1.0.0",
    # 第三方服务镜像
    "neo4j:5.26",
    "quay.io/coreos/etcd:v3.5.5",
    "minio/minio:RELEASE.2023-03-20T20-16-18Z",
    "milvusdb/milvus:v2.5.6"
)

$OutputFile = "$OutputDir\smart_water_images_$DateTime.tar"

Write-Host "  导出基础服务镜像..." -ForegroundColor Gray
docker save $ExportImages -o $OutputFile

if ($LASTEXITCODE -eq 0) {
    $FileInfo = Get-Item $OutputFile
    $FileSizeGB = [math]::Round($FileInfo.Length / 1GB, 2)
    Write-Host "  ✓ 导出成功: $OutputFile ($FileSizeGB GB)" -ForegroundColor Green
} else {
    Write-Host "  ✗ 导出失败" -ForegroundColor Red
    exit 1
}

# 导出 GPU 镜像（单独文件，因为很大）
if ($IncludeGpu) {
    $GpuOutputFile = "$OutputDir\smart_water_gpu_images_$DateTime.tar"
    Write-Host "  导出 GPU 服务镜像..." -ForegroundColor Gray
    
    $GpuExportImages = @(
        "mineru-sglang:latest",
        "paddlex:latest"
    )
    docker save $GpuExportImages -o $GpuOutputFile
    
    if ($LASTEXITCODE -eq 0) {
        $GpuFileInfo = Get-Item $GpuOutputFile
        $GpuFileSizeGB = [math]::Round($GpuFileInfo.Length / 1GB, 2)
        Write-Host "  ✓ GPU 镜像导出成功: $GpuOutputFile ($GpuFileSizeGB GB)" -ForegroundColor Green
    }
}

# ============================================================
# 步骤 4: 生成部署清单
# ============================================================
Write-Host "`n[4/4] 生成部署清单..." -ForegroundColor Yellow

$Manifest = @"
# Smart Water 内网部署清单
# 生成时间: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## 需要复制的文件

### 1. Docker 镜像文件
- $OutputFile

### 2. 项目代码（整个目录）
- Yuxi-Know-main/

### 3. 环境配置文件
- .env（需要根据内网环境修改）

## 内网机器部署步骤

1. 加载 Docker 镜像:
   docker load -i smart_water_images_$DateTime.tar

2. 进入项目目录:
   cd Yuxi-Know-main

3. 配置环境变量:
   copy .env.template .env
   # 编辑 .env 文件

4. 启动服务:
   .\deploy.ps1 start

5. 访问服务:
   - 前端: http://localhost:5173
   - API:  http://localhost:5050/docs
"@

$ManifestFile = "$OutputDir\部署清单_$DateTime.txt"
$Manifest | Out-File -FilePath $ManifestFile -Encoding UTF8
Write-Host "  ✓ 部署清单: $ManifestFile" -ForegroundColor Green

# ============================================================
# 完成
# ============================================================
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  打包完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`n请将以下内容复制到 U 盘:" -ForegroundColor Cyan
Write-Host "  1. $OutputDir\ 目录（镜像文件）"
Write-Host "  2. Yuxi-Know-main\ 目录（项目代码）"

if ($IncludeGpu) {
    Write-Host "`n⚠️  GPU 镜像文件较大，请确保 U 盘空间足够" -ForegroundColor Yellow
}

Write-Host "`n在内网机器上执行:" -ForegroundColor Cyan
Write-Host "  docker load -i smart_water_images_$DateTime.tar"
Write-Host "  cd Yuxi-Know-main"
Write-Host "  .\deploy.ps1 start"
Write-Host ""