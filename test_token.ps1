# Simple Token Test Script
Write-Host "🧪 Testing Current Token..." -ForegroundColor Cyan

# Check if token file exists
if (-not (Test-Path "token.config")) {
    Write-Host "❌ token.config file not found!" -ForegroundColor Red
    exit 1
}

# Load token
$token = Get-Content "token.config" -Raw
$token = $token.Trim()

Write-Host "✅ Token file found" -ForegroundColor Green
Write-Host "   Length: $($token.Length) characters" -ForegroundColor White
Write-Host "   Preview: $($token.Substring(0, [Math]::Min(50, $token.Length)))..." -ForegroundColor White

# Test API call
Write-Host "`n🔄 Testing API connection..." -ForegroundColor Yellow

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$body = @{
    queryText = "test connection"
    skill = "Product_azzEXjGzazCl78XgkHBkV"
    options = @("GetResultsSummary")
} | ConvertTo-Json

$apiUrl = "https://aurorabapenv87b96.crm10.dynamics.com/api/copilot/v1.0/queryskillstructureddata"

try {
    $response = Invoke-RestMethod -Uri $apiUrl -Method POST -Headers $headers -Body $body -TimeoutSec 30
    Write-Host "✅ API test successful!" -ForegroundColor Green
    Write-Host "   Response received with data" -ForegroundColor White
    
    # Show response summary
    if ($response.results) {
        Write-Host "   Found $($response.results.Count) results" -ForegroundColor White
    }
    
    Write-Host "`n🎉 Token is working correctly!" -ForegroundColor Green
}
catch {
    Write-Host "❌ API test failed!" -ForegroundColor Red
    
    $statusCode = $null
    if ($_.Exception.Response) {
        $statusCode = [int]$_.Exception.Response.StatusCode
        Write-Host "   Status Code: $statusCode" -ForegroundColor Red
    }
    
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($statusCode -eq 401 -or $statusCode -eq 403) {
        Write-Host "`n🔄 TOKEN REFRESH REQUIRED!" -ForegroundColor Yellow
        Write-Host "   Your token appears to be expired or invalid." -ForegroundColor White
        Write-Host "   Please follow the token refresh instructions." -ForegroundColor White
    }
}

Write-Host "`n" -NoNewline