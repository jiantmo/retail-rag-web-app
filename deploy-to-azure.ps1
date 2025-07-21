# Azure部署脚本
# 请在部署前确保已安装Azure CLI并登录

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$WebAppName,
    
    [Parameter(Mandatory=$true)]
    [string]$Location = "East Asia",
    
    [Parameter(Mandatory=$false)]
    [string]$AppServicePlanName = "$WebAppName-plan",
    
    [Parameter(Mandatory=$false)]
    [string]$Sku = "F1"
)

Write-Host "Starting deployment of Retail RAG Web App to Azure..." -ForegroundColor Green

# Check if Azure CLI is logged in
Write-Host "Checking Azure CLI login status..." -ForegroundColor Yellow
$accountInfo = az account show 2>$null
if (-not $accountInfo) {
    Write-Host "Please login to Azure CLI first: az login" -ForegroundColor Red
    exit 1
}

Write-Host "Azure CLI is logged in" -ForegroundColor Green

# Create resource group (if not exists)
Write-Host "Creating resource group: $ResourceGroupName" -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location

# Create App Service plan
Write-Host "Creating App Service plan: $AppServicePlanName" -ForegroundColor Yellow
az appservice plan create --name $AppServicePlanName --resource-group $ResourceGroupName --sku $Sku --location $Location

# Create Web App
Write-Host "Creating Web App: $WebAppName" -ForegroundColor Yellow
az webapp create --name $WebAppName --resource-group $ResourceGroupName --plan $AppServicePlanName --runtime "DOTNET|8.0"

# Configure Web App settings
Write-Host "Configuring Web App settings..." -ForegroundColor Yellow
az webapp config set --name $WebAppName --resource-group $ResourceGroupName --startup-file ""

# 构建和发布应用
Write-Host "Building application..." -ForegroundColor Yellow
dotnet clean
dotnet restore
dotnet build --configuration Release

Write-Host "Publishing application..." -ForegroundColor Yellow
dotnet publish --configuration Release --output "./publish"

# 部署到Azure
Write-Host "Deploying to Azure..." -ForegroundColor Yellow
Compress-Archive -Path "./publish/*" -DestinationPath "./deploy.zip" -Force
az webapp deploy --resource-group $ResourceGroupName --name $WebAppName --src-path "./deploy.zip" --type zip

# Configure application settings (environment variables)
Write-Host "Configuring application environment variables..." -ForegroundColor Yellow
Write-Host "Please manually configure the following application settings in Azure Portal:" -ForegroundColor Yellow
Write-Host "  - AZURE_OPENAI_ENDPOINT" -ForegroundColor Cyan
Write-Host "  - AZURE_OPENAI_API_KEY" -ForegroundColor Cyan  
Write-Host "  - AZURE_OPENAI_DEPLOYMENT_NAME" -ForegroundColor Cyan
Write-Host "  - AZURE_SEARCH_SERVICE_NAME" -ForegroundColor Cyan
Write-Host "  - AZURE_SEARCH_API_KEY" -ForegroundColor Cyan
Write-Host "  - AZURE_SEARCH_INDEX_NAME" -ForegroundColor Cyan

# Get Web App URL
$webAppUrl = az webapp show --name $WebAppName --resource-group $ResourceGroupName --query "defaultHostName" --output tsv
Write-Host "Deployment completed!" -ForegroundColor Green
Write-Host "Application URL: https://$webAppUrl" -ForegroundColor Green
Write-Host "Azure Portal: https://portal.azure.com" -ForegroundColor Cyan

# Clean up temporary files
Remove-Item "./deploy.zip" -ErrorAction SilentlyContinue
Write-Host "Cleanup completed" -ForegroundColor Green
