# PowerShell script to test Dataverse Search API
# Based on multi_thread_unified_search.py configuration

param(
    [Parameter(Mandatory=$true)]
    [string]$Query,
    
    [string]$Skill = "Product_azzEXjGzazCl78XgkHBkV",
    
    [switch]$GetToken
)

# OAuth2 Configuration (from multi_thread_unified_search.py)
$TenantId = "4abc24ea-2d0b-4011-87d4-3de32ca1e9cc"
$ClientId = "51f81489-12ee-4a9e-aaae-a2591f45987d"
$Resource = "https://aurorabapenv87b96.crm10.dynamics.com/"
$BaseUrl = "https://aurorabapenv87b96.crm10.dynamics.com/api/copilot/v1.0/queryskillstructureddata"

# Token file path
$TokenFile = "token.config"

function Get-AccessToken {
    param(
        [switch]$ForceRefresh
    )
    
    # Check if token file exists and is recent (less than 50 minutes old)
    if (!$ForceRefresh -and (Test-Path $TokenFile)) {
        $tokenAge = (Get-Date) - (Get-Item $TokenFile).LastWriteTime
        if ($tokenAge.TotalMinutes -lt 50) {
            $token = Get-Content $TokenFile -Raw
            if ($token) {
                Write-Host "✅ Using cached token (age: $([math]::Round($tokenAge.TotalMinutes, 1)) minutes)" -ForegroundColor Green
                return $token.Trim()
            }
        }
    }
    
    Write-Host "🔄 Getting new access token using device code flow..." -ForegroundColor Yellow
    
    # Step 1: Get device code
    $deviceCodeEndpoint = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/devicecode"
    $deviceData = @{
        'client_id' = $ClientId
        'scope' = "$($Resource)user_impersonation"
    }
    
    try {
        $deviceResponse = Invoke-RestMethod -Uri $deviceCodeEndpoint -Method POST -Body $deviceData -ContentType "application/x-www-form-urlencoded"
        
        Write-Host "`n📱 Device Code Authentication Required:" -ForegroundColor Cyan
        Write-Host "1. Go to: $($deviceResponse.verification_uri)" -ForegroundColor White
        Write-Host "2. Enter code: $($deviceResponse.user_code)" -ForegroundColor Yellow
        Write-Host "3. Sign in with your Microsoft account" -ForegroundColor White
        Write-Host "`nWaiting for authentication..." -ForegroundColor Gray
        
        # Step 2: Poll for token
        $tokenEndpoint = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"
        $tokenData = @{
            'grant_type' = 'urn:ietf:params:oauth:grant-type:device_code'
            'client_id' = $ClientId
            'device_code' = $deviceResponse.device_code
        }
        
        $maxAttempts = [math]::Ceiling($deviceResponse.expires_in / $deviceResponse.interval)
        
        for ($i = 0; $i -lt $maxAttempts; $i++) {
            Start-Sleep -Seconds $deviceResponse.interval
            
            try {
                $tokenResponse = Invoke-RestMethod -Uri $tokenEndpoint -Method POST -Body $tokenData -ContentType "application/x-www-form-urlencoded"
                
                # Save tokens
                $tokenResponse.access_token | Set-Content $TokenFile -NoNewline
                
                Write-Host "✅ Authentication successful! Token saved." -ForegroundColor Green
                return $tokenResponse.access_token
            }
            catch {
                $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
                if ($errorDetails.error -eq "authorization_pending") {
                    Write-Host "." -NoNewline -ForegroundColor Gray
                    continue
                }
                elseif ($errorDetails.error -eq "slow_down") {
                    Start-Sleep -Seconds ($deviceResponse.interval * 2)
                    continue
                }
                else {
                    throw "Authentication failed: $($errorDetails.error_description)"
                }
            }
        }
        
        throw "Authentication timed out. Please try again."
    }
    catch {
        Write-Error "Failed to get access token: $($_.Exception.Message)"
        return $null
    }
}

function Invoke-DataverseSearch {
    param(
        [string]$QueryText,
        [string]$AccessToken,
        [string]$SkillName = "Product_azzEXjGzazCl78XgkHBkV"
    )
    
    $headers = @{
        "Content-Type" = "application/json"
        "User-Agent" = "PowerShell-DataverseTest/1.0"
        "x-ms-crm-query-language" = "1033"
        "x-ms-crm-service-root-url" = "https://aurorabapenv87b96.crm10.dynamics.com/"
        "x-ms-crm-userid" = "aurorauser01@aurorafinanceintegration02.onmicrosoft.com"
        "x-ms-organization-id" = "440a70c9-ff61-f011-beb8-6045bd09e9cc"
        "x-ms-user-agent" = "PowerVA/2"
        "Authorization" = "Bearer $AccessToken"
        "Connection" = "keep-alive"
    }
    
    $payload = @{
        "queryText" = $QueryText
        "skill" = $SkillName
        "options" = @("GetResultsSummary")
        "additionalProperties" = @{
            "ExecuteUnifiedSearch" = $true
        }
    } | ConvertTo-Json -Depth 10
    
    try {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        
        Write-Host "🔍 Searching Dataverse for: '$QueryText'" -ForegroundColor Cyan
        Write-Host "🎯 Using skill: $SkillName" -ForegroundColor Gray
        
        $response = Invoke-RestMethod -Uri $BaseUrl -Method POST -Headers $headers -Body $payload -ContentType "application/json"
        
        $stopwatch.Stop()
        
        Write-Host "✅ Search completed in $($stopwatch.ElapsedMilliseconds)ms" -ForegroundColor Green
        
        return $response
    }
    catch {
        $stopwatch.Stop()
        Write-Error "❌ Search failed after $($stopwatch.ElapsedMilliseconds)ms: $($_.Exception.Message)"
        
        if ($_.Exception.Response) {
            $statusCode = $_.Exception.Response.StatusCode
            Write-Host "Status Code: $statusCode" -ForegroundColor Red
            
            if ($statusCode -eq 401) {
                Write-Host "💡 Token might be expired. Try running with -GetToken switch to refresh." -ForegroundColor Yellow
            }
        }
        
        return $null
    }
}

# Main execution
Write-Host "🚀 Dataverse Search API Test" -ForegroundColor Magenta
Write-Host "=============================" -ForegroundColor Magenta

# Get access token
$accessToken = Get-AccessToken -ForceRefresh:$GetToken

if (-not $accessToken) {
    Write-Error "❌ Failed to obtain access token. Exiting."
    exit 1
}

# Perform search
$result = Invoke-DataverseSearch -QueryText $Query -AccessToken $accessToken -SkillName $Skill

if ($result) {
    Write-Host "`n📊 Search Results:" -ForegroundColor Green
    Write-Host "=================" -ForegroundColor Green
    
    # Pretty print the result
    $result | ConvertTo-Json -Depth 20 | Write-Host
    
    # Extract some key metrics
    if ($result.PSObject.Properties.Name -contains "queryResult") {
        $queryResult = $result.queryResult
        if ($queryResult -and $queryResult.PSObject.Properties.Name -contains "value") {
            $resultCount = $queryResult.value.Count
            Write-Host "`n📈 Found $resultCount results" -ForegroundColor Green
        }
    }
}
else {
    Write-Host "❌ No results returned or search failed." -ForegroundColor Red
}

Write-Host "`n✨ Test completed!" -ForegroundColor Magenta
