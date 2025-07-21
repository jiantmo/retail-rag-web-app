# 快速部署脚本 - 使用默认设置
param(
    [Parameter(Mandatory=$true)]
    [string]$AppName
)

$ResourceGroup = "$AppName-rg"
$Location = "East Asia"

Write-Host "Quick deploying $AppName to Azure East Asia..." -ForegroundColor Green

# 调用主部署脚本
.\deploy-to-azure.ps1 -ResourceGroupName $ResourceGroup -WebAppName $AppName -Location $Location

Write-Host "Next Steps After Deployment:" -ForegroundColor Yellow
Write-Host "1. Visit Azure Portal: https://portal.azure.com" -ForegroundColor Cyan
Write-Host "2. Navigate to your Web App: $AppName" -ForegroundColor Cyan
Write-Host "3. Go to Configuration -> Application Settings" -ForegroundColor Cyan
Write-Host "4. Add the following required environment variables:" -ForegroundColor Cyan
Write-Host "   - AZURE_OPENAI_ENDPOINT: Your Azure OpenAI service endpoint" -ForegroundColor White
Write-Host "   - AZURE_OPENAI_API_KEY: Your Azure OpenAI API key" -ForegroundColor White
Write-Host "   - AZURE_OPENAI_DEPLOYMENT_NAME: Your GPT model deployment name" -ForegroundColor White
Write-Host "   - AZURE_SEARCH_SERVICE_NAME: Your Azure search service name" -ForegroundColor White
Write-Host "   - AZURE_SEARCH_API_KEY: Your Azure search API key" -ForegroundColor White
Write-Host "   - AZURE_SEARCH_INDEX_NAME: Your search index name" -ForegroundColor White
Write-Host "5. Click Save and restart the application" -ForegroundColor Cyan
