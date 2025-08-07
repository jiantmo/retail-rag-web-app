# Working Single Question Test
param(
    [string]$TokenFile = "token.config"
)

Write-Host "Simple API Test" -ForegroundColor Green

try {
    $token = (Get-Content -Path $TokenFile -Raw).Trim()
    Write-Host "Token loaded" -ForegroundColor Green
} catch {
    Write-Error "Cannot load token: $($_.Exception.Message)"
    exit 1
}

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
    "User-Agent" = "insomnia/11.4.0"
    "x-ms-crm-query-language" = "1033"
    "x-ms-crm-service-root-url" = "https://aurorabapenv87b96.crm10.dynamics.com/"
    "x-ms-crm-userid" = "aurorauser01@aurorafinanceintegration02.onmicrosoft.com"
    "x-ms-organization-id" = "440a70c9-ff61-f011-beb8-6045bd09e9cc"
    "x-ms-user-agent" = "PowerVA/2"
}

$apiUrl = "https://aurorabapenv87b96.crm10.dynamics.com/api/copilot/v1.0/queryskillstructureddata"
$testQuestion = "What tents are available?"

$body = @{
    queryText = $testQuestion
    skill = "Product_k0BVJ0Ao4wc1kdzVKjAUj"
    options = @("GetResultsSummary")
    additionalProperties = @{
        ExecuteUnifiedSearch = $true
    }
} | ConvertTo-Json -Depth 10

Write-Host "Testing: $testQuestion" -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri $apiUrl -Method Post -Headers $headers -Body $body -TimeoutSec 30
    
    Write-Host "SUCCESS!" -ForegroundColor Green
    if ($response.queryResult -and $response.queryResult.summary) {
        Write-Host "Got summary response" -ForegroundColor Cyan
        return $true
    } else {
        Write-Host "Got response but no summary" -ForegroundColor Yellow
        return $true
    }
    
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $statusCode = [int]$_.Exception.Response.StatusCode
        Write-Host "Status: $statusCode" -ForegroundColor Red
    }
    
    return $false
}