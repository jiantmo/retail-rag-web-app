# Azure Web App 部署脚本
# 部署 retail-rag-web-app 到 Azure App Service

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "jiantmo-rg",
    
    [Parameter(Mandatory=$false)]
    [string]$AppServiceName = "jiantmo-retail-rag-web-app",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "North Central US",
    
    [Parameter(Mandatory=$false)]
    [string]$SubscriptionId = "0f7690ff-3bdf-4d45-9eda-cabd997016d8",
    
    [Parameter(Mandatory=$false)]
    [string]$AppServicePlan = "jiantmo-retail-app-plan"
)

Write-Host "🚀 开始部署 retail-rag-web-app 到 Azure..." -ForegroundColor Green

# 1. 登录 Azure（如果需要）
Write-Host "🔐 检查 Azure 登录状态..." -ForegroundColor Cyan
try {
    $context = az account show 2>$null | ConvertFrom-Json
    if ($context) {
        Write-Host "✅ 已登录 Azure，当前订阅: $($context.name)" -ForegroundColor Green
        Write-Host "   订阅 ID: $($context.id)" -ForegroundColor White
    }
} catch {
    Write-Host "❌ 未登录 Azure，请先登录..." -ForegroundColor Red
    Write-Host "💡 运行: az login" -ForegroundColor Yellow
    exit 1
}

# 2. 设置正确的订阅
Write-Host "📋 设置订阅..." -ForegroundColor Cyan
az account set --subscription $SubscriptionId
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 设置订阅失败" -ForegroundColor Red
    exit 1
}

# 3. 检查资源组
Write-Host "📁 检查资源组: $ResourceGroupName..." -ForegroundColor Cyan
$rgExists = az group exists --name $ResourceGroupName
if ($rgExists -eq "false") {
    Write-Host "📁 创建资源组: $ResourceGroupName..." -ForegroundColor Yellow
    az group create --name $ResourceGroupName --location $Location
}
Write-Host "✅ 资源组已就绪" -ForegroundColor Green

# 4. 检查/创建 App Service Plan
Write-Host "📊 检查 App Service Plan: $AppServicePlan..." -ForegroundColor Cyan
$planExists = az appservice plan show --name $AppServicePlan --resource-group $ResourceGroupName 2>$null
if (-not $planExists) {
    Write-Host "📊 创建 App Service Plan..." -ForegroundColor Yellow
    az appservice plan create `
        --name $AppServicePlan `
        --resource-group $ResourceGroupName `
        --location $Location `
        --sku B1 `
        --is-linux
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 创建 App Service Plan 失败" -ForegroundColor Red
        exit 1
    }
}
Write-Host "✅ App Service Plan 已就绪" -ForegroundColor Green

# 5. 检查/创建 Web App
Write-Host "🌐 检查 Web App: $AppServiceName..." -ForegroundColor Cyan
$appExists = az webapp show --name $AppServiceName --resource-group $ResourceGroupName 2>$null
if (-not $appExists) {
    Write-Host "🌐 创建 Web App..." -ForegroundColor Yellow
    az webapp create `
        --name $AppServiceName `
        --resource-group $ResourceGroupName `
        --plan $AppServicePlan `
        --runtime "DOTNETCORE:8.0"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 创建 Web App 失败" -ForegroundColor Red
        exit 1
    }
}
Write-Host "✅ Web App 已就绪" -ForegroundColor Green

# 6. 配置 Web App 设置
Write-Host "⚙️ 配置应用设置..." -ForegroundColor Cyan

# 读取 .env 文件并设置应用配置
$envFile = ".env"
if (Test-Path $envFile) {
    $envVars = @{}
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            $envVars[$key] = $value
        }
    }
    
    # 设置应用配置
    foreach ($key in $envVars.Keys) {
        $value = $envVars[$key]
        Write-Host "   设置: $key" -ForegroundColor White
        az webapp config appsettings set `
            --name $AppServiceName `
            --resource-group $ResourceGroupName `
            --settings "$key=$value" > $null
    }
}

# 7. 启用系统分配的托管标识
Write-Host "🔑 启用系统分配的托管标识..." -ForegroundColor Cyan
az webapp identity assign `
    --name $AppServiceName `
    --resource-group $ResourceGroupName > $null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 托管标识已启用" -ForegroundColor Green
} else {
    Write-Host "⚠️ 托管标识配置可能失败，但继续部署" -ForegroundColor Yellow
}

# 8. 构建项目
Write-Host "🔨 构建项目..." -ForegroundColor Cyan
dotnet clean
dotnet restore
dotnet build --configuration Release

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 项目构建失败" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 项目构建成功" -ForegroundColor Green

# 9. 发布项目
Write-Host "📦 发布项目..." -ForegroundColor Cyan
dotnet publish --configuration Release --output ./publish

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 项目发布失败" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 项目发布成功" -ForegroundColor Green

# 10. 部署到 Azure
Write-Host "🚀 部署到 Azure Web App..." -ForegroundColor Cyan

# 创建部署包
Compress-Archive -Path "./publish/*" -DestinationPath "./deploy.zip" -Force

# 部署
az webapp deployment source config-zip `
    --name $AppServiceName `
    --resource-group $ResourceGroupName `
    --src "./deploy.zip"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 部署成功!" -ForegroundColor Green
    
    # 清理临时文件
    Remove-Item "./deploy.zip" -Force -ErrorAction SilentlyContinue
    Remove-Item "./publish" -Recurse -Force -ErrorAction SilentlyContinue
    
    # 获取应用 URL
    $appUrl = az webapp show --name $AppServiceName --resource-group $ResourceGroupName --query "defaultHostName" --output tsv
    Write-Host "🌐 应用 URL: https://$appUrl" -ForegroundColor Green
    Write-Host "🎉 部署完成!" -ForegroundColor Green
    
    # 显示应用日志链接
    Write-Host "📋 查看应用日志:" -ForegroundColor Yellow
    Write-Host "   az webapp log tail --name $AppServiceName --resource-group $ResourceGroupName" -ForegroundColor White
    
} else {
    Write-Host "❌ 部署失败" -ForegroundColor Red
    exit 1
}
