# 蓝牙心率到VRChat OSC转发器启动脚本
# PowerShell版本

# 设置控制台编码为UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "蓝牙心率到VRChat OSC转发器"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "蓝牙心率到VRChat OSC转发器" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查Python是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ 发现Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: 未找到Python，请先安装Python 3.7+" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

# 检查是否在正确的目录
if (-not (Test-Path "main.py")) {
    Write-Host "❌ 错误: 未找到main.py文件" -ForegroundColor Red
    Write-Host "请确保在bluetooth-heartrate文件夹中运行此脚本" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

# 检查依赖是否安装
Write-Host "🔍 检查Python依赖..." -ForegroundColor Yellow
try {
    python -c "import bleak, pythonosc" 2>$null
    Write-Host "✓ 依赖检查完成" -ForegroundColor Green
} catch {
    Write-Host "📦 正在安装Python依赖..." -ForegroundColor Yellow
    try {
        pip install -r requirements.txt
        Write-Host "✓ 依赖安装完成" -ForegroundColor Green
    } catch {
        Write-Host "❌ 错误: 依赖安装失败" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
}

Write-Host ""
Write-Host "🚀 启动蓝牙心率转发器..." -ForegroundColor Green
Write-Host "💡 按 Ctrl+C 可以退出程序" -ForegroundColor Yellow
Write-Host ""

# 运行主程序
try {
    python main.py
} catch {
    Write-Host ""
    Write-Host "❌ 程序运行出错" -ForegroundColor Red
}

Write-Host ""
Write-Host "程序已退出" -ForegroundColor Gray
Read-Host "按回车键关闭窗口"