# BTC 自动交易系统 - Windows 启动脚本

param(
    [string]$Mode = "dev"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Set-Location $ProjectDir

switch ($Mode) {
    "dev" {
        Write-Host "启动开发环境..." -ForegroundColor Green
        docker-compose -f docker-compose.dev.yml up -d
        
        Write-Host "等待服务启动..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        Write-Host "初始化 QuestDB 表..." -ForegroundColor Yellow
        $sql = Get-Content "scripts/init_questdb.sql" -Raw
        try {
            Invoke-RestMethod -Uri "http://localhost:9000/exec" -Method Get -Body @{query=$sql} | Out-Null
        } catch {
            Write-Host "QuestDB 初始化跳过（可能已存在）" -ForegroundColor Gray
        }
        
        Write-Host ""
        Write-Host "服务已启动:" -ForegroundColor Green
        Write-Host "  - API: http://localhost:8000"
        Write-Host "  - QuestDB: http://localhost:9000"
        Write-Host "  - Kafka: localhost:9092"
    }
    "prod" {
        Write-Host "启动生产环境..." -ForegroundColor Green
        docker-compose up -d
        
        Write-Host "等待服务启动..." -ForegroundColor Yellow
        Start-Sleep -Seconds 15
        
        Write-Host "初始化 QuestDB 表..." -ForegroundColor Yellow
        $sql = Get-Content "scripts/init_questdb.sql" -Raw
        try {
            Invoke-RestMethod -Uri "http://localhost:9000/exec" -Method Get -Body @{query=$sql} | Out-Null
        } catch {}
        
        Write-Host "服务已启动" -ForegroundColor Green
    }
    "stop" {
        Write-Host "停止服务..." -ForegroundColor Yellow
        docker-compose -f docker-compose.dev.yml down 2>$null
        docker-compose down 2>$null
        Write-Host "服务已停止" -ForegroundColor Green
    }
    "logs" {
        docker-compose logs -f
    }
    default {
        Write-Host "用法: .\start.ps1 -Mode {dev|prod|stop|logs}"
        exit 1
    }
}
