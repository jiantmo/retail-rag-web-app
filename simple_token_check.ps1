# Simple Token Validation
param([switch]$TestAPI)

Write-Host "🔍 Simple Token Check" -ForegroundColor Cyan

# Load token
if (Test-Path "token.config") {
    $token = (Get-Content "token.config" -Raw).Trim()
    Write-Host "✅ Token loaded (length: $($token.Length))" -ForegroundColor Green
    
    # Basic JWT validation - check if it has 3 parts
    $parts = $token.Split('.')
    if ($parts.Length -eq 3) {
        Write-Host "✅ Token format appears valid (3 parts)" -ForegroundColor Green
        
        # Show token preview  
        $preview = $token.Substring(0, [Math]::Min(50, $token.Length)) + "..."
        Write-Host "   Preview: $preview" -ForegroundColor White
    } else {
        Write-Host "❌ Invalid token format (expected 3 parts, got $($parts.Length))" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "❌ token.config file not found" -ForegroundColor Red
    exit 1
}

Write-Host "`n🔄 Token Generation URL:" -ForegroundColor Cyan
$url = "https://login.microsoftonline.com/common/oauth2/authorize"
$params = "client_id=51f81489-12ee-4a9e-aaae-a2591f45987d"
$params += "&response_type=token"
$params += "&redirect_uri=https://localhost" 
$params += "&resource=https://aurorabapenv87b96.crm10.dynamics.com/"
$params += "&prompt=login"

Write-Host "$url" -ForegroundColor Yellow
Write-Host "?$params" -ForegroundColor Yellow

if ($TestAPI) {
    Write-Host "`n🧪 Testing API Connection..." -ForegroundColor Cyan
    try {
        $headers = @{
            "Authorization" = "Bearer $token"
            "Content-Type" = "application/json"  
        }
        
        $body = @{
            queryText = "test"
            skill = "Product_azzEXjGzazCl78XgkHBkV"
            options = @("GetResultsSummary")
        } | ConvertTo-Json
        
        $uri = "https://aurorabapenv87b96.crm10.dynamics.com/api/copilot/v1.0/queryskillstructureddata"
        
        $response = Invoke-RestMethod -Uri $uri -Method POST -Headers $headers -Body $body -TimeoutSec 30
        Write-Host "✅ API test successful" -ForegroundColor Green
    }
    catch {
        $errorMsg = $_.Exception.Message
        if ($errorMsg -match "401" -or $errorMsg -match "403") {
            Write-Host "❌ Authentication failed - token may be expired" -ForegroundColor Red
        } else {
            Write-Host "⚠️  API test failed: $errorMsg" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n📋 Instructions:" -ForegroundColor White
Write-Host "1. To test API: .\simple_token_check.ps1 -TestAPI" -ForegroundColor White
Write-Host "2. To refresh token: Open the URL above in browser" -ForegroundColor White
Write-Host "3. Copy access_token from redirect URL to token.config" -ForegroundColor White