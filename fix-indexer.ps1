# 使用托管身份删除 Knowledge Agent
# retail-knowledge-agent 删除脚本

Write-Host "🗑️ 使用托管身份删除 retail-knowledge-agent..." -ForegroundColor Yellow

$searchServiceName = "mos-acs"
$agentName = "retail-knowledge-agent"
$resourceGroup = "t-mos"

# 获取访问令牌
Write-Host "🔐 获取托管身份访问令牌..." -ForegroundColor Cyan
try {
    $tokenResponse = Invoke-RestMethod -Uri "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://search.azure.com/" -Headers @{Metadata="true"} -Method GET
    $accessToken = $tokenResponse.access_token
    Write-Host "✅ 成功获取访问令牌" -ForegroundColor Green
} catch {
    Write-Host "❌ 无法获取访问令牌: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 如果在本地运行，请使用 Azure CLI 或部署到有托管身份的环境" -ForegroundColor Yellow
    exit 1
}

# 删除 skillset (Knowledge Agent)
Write-Host "🔄 删除 Knowledge Agent skillset..." -ForegroundColor Cyan
$headers = @{
    'Authorization' = "Bearer $accessToken"
    'Content-Type' = 'application/json'
}

$skillsetUrl = "https://$searchServiceName.search.windows.net/skillsets('$agentName')?api-version=2023-07-01-preview"

try {
    $response = Invoke-RestMethod -Uri $skillsetUrl -Headers $headers -Method DELETE
    Write-Host "✅ 成功删除 Knowledge Agent: $agentName" -ForegroundColor Green
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 404) {
        Write-Host "ℹ️ Knowledge Agent '$agentName' 不存在或已被删除" -ForegroundColor Blue
    } else {
        Write-Host "❌ 删除失败: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "状态码: $statusCode" -ForegroundColor Red
    }
}

Write-Host "🎉 删除操作完成!" -ForegroundColor Green