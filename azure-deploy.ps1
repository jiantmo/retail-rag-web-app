# Quick Azure Deployment Script for Retail RAG Web App
# Run this in PowerShell with Azure CLI installed

# Configuration
$resourceGroupName = "jiantmo-rg"
$location = "East US"
$appServicePlanName = "retail-rag-plan"
$webAppName = "jiantmo-retail-rag-web-app"
$subscriptionId = "$(az account show --query id --output tsv)"  # Get current subscription automatically

Write-Host "🚀 Starting Azure deployment for Retail RAG Web App" -ForegroundColor Green
Write-Host "Web App Name: $webAppName" -ForegroundColor Cyan

# Check Azure CLI login
Write-Host "📋 Checking Azure CLI login status..." -ForegroundColor Yellow
try {
    az account show | Out-Null
    Write-Host "✅ Azure CLI is logged in" -ForegroundColor Green
} catch {
    Write-Host "❌ Please login to Azure CLI first:" -ForegroundColor Red
    Write-Host "az login" -ForegroundColor Yellow
    exit 1
}

# Set subscription
Write-Host "📋 Setting subscription..." -ForegroundColor Yellow
az account set --subscription $subscriptionId

# Check if resource group exists
Write-Host "� Checking resource group: $resourceGroupName" -ForegroundColor Yellow
$rgExists = az group exists --name $resourceGroupName
if ($rgExists -eq "true") {
    Write-Host "✅ Resource group exists" -ForegroundColor Green
} else {
    Write-Host "❌ Resource group '$resourceGroupName' not found. Please create it first." -ForegroundColor Red
    exit 1
}

# Create App Service Plan
Write-Host "📦 Creating App Service Plan: $appServicePlanName" -ForegroundColor Yellow
az appservice plan create --name $appServicePlanName --resource-group $resourceGroupName --sku "B1" --is-linux

# Create Web App
Write-Host "📦 Creating Web App: $webAppName" -ForegroundColor Yellow
az webapp create --resource-group $resourceGroupName --plan $appServicePlanName --name $webAppName --runtime "DOTNETCORE:8.0"

# Configure app settings
Write-Host "⚙️  Configuring app settings..." -ForegroundColor Yellow
az webapp config appsettings set --resource-group $resourceGroupName --name $webAppName --settings ASPNETCORE_ENVIRONMENT=Production WEBSITES_ENABLE_APP_SERVICE_STORAGE=false WEBSITE_RUN_FROM_PACKAGE=1

# Enable system-assigned managed identity
Write-Host "🔐 Enabling managed identity..." -ForegroundColor Yellow
az webapp identity assign --resource-group $resourceGroupName --name $webAppName

# Deploy application (if publish folder exists)
if (Test-Path "./publish") {
    Write-Host "📤 Deploying application..." -ForegroundColor Yellow
    
    # Create ZIP file
    $publishPath = Resolve-Path "./publish"
    $zipPath = "./app.zip"
    
    # Remove existing zip if it exists
    if (Test-Path $zipPath) {
        Remove-Item $zipPath -Force
    }
    
    # Create zip archive
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($publishPath, $zipPath)
    
    # Deploy via ZIP
    az webapp deployment source config-zip --resource-group $resourceGroupName --name $webAppName --src $zipPath
    
    Write-Host "🎉 Application deployed successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Publish folder not found. Run 'dotnet publish -c Release -o ./publish' first." -ForegroundColor Yellow
}

# Get publish profile for GitHub Actions
Write-Host "📋 Getting publish profile for GitHub Actions..." -ForegroundColor Yellow
az webapp deployment list-publishing-profiles --resource-group $resourceGroupName --name $webAppName --xml > publish-profile.xml

Write-Host ""
Write-Host "✅ Deployment completed!" -ForegroundColor Green
Write-Host "🌐 Web App URL: https://$webAppName.azurewebsites.net" -ForegroundColor Cyan
Write-Host "📁 Publish profile saved to: publish-profile.xml" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Yellow
Write-Host "1. Configure environment variables in Azure Portal:" -ForegroundColor White
Write-Host "   - AZURE_SEARCH_ENDPOINT" -ForegroundColor Gray
Write-Host "   - AZURE_OPENAI_ENDPOINT" -ForegroundColor Gray
Write-Host "   - AZURE_SEARCH_INDEX_NAME" -ForegroundColor Gray
Write-Host "   - AZURE_SEARCH_AGENT_NAME" -ForegroundColor Gray
Write-Host "   - AZURE_OPENAI_GPT_DEPLOYMENT" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Grant managed identity permissions to:" -ForegroundColor White
Write-Host "   - Azure Search Service (Search Service Contributor)" -ForegroundColor Gray
Write-Host "   - Azure OpenAI Service (Cognitive Services User)" -ForegroundColor Gray
Write-Host ""
Write-Host "3. For GitHub Actions deployment:" -ForegroundColor White
Write-Host "   - Copy publish-profile.xml content to GitHub Secrets as 'AZUREAPPSERVICE_PUBLISHPROFILE'" -ForegroundColor Gray
Write-Host "   - Update AZURE_WEBAPP_NAME in .github/workflows/azure-deploy.yml to: $webAppName" -ForegroundColor Gray
