# Enhanced API Testing Script
# Tests multiple scenarios similar to multi_thread_runner.py

param(
    [int]$TestCount = 5,
    [int]$DelaySeconds = 1
)

Write-Host "🚀 Enhanced API Testing (Simulating Multi-Thread Runner)" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray

# Load token
if (-not (Test-Path "token.config")) {
    Write-Host "❌ token.config file not found!" -ForegroundColor Red
    exit 1
}

$token = (Get-Content "token.config" -Raw).Trim()
Write-Host "✅ Token loaded ($($token.Length) characters)" -ForegroundColor Green

# API configuration
$apiUrl = "https://aurorabapenv87b96.crm10.dynamics.com/api/copilot/v1.0/queryskillstructureddata"
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Test questions (similar to what we improved in test cases)
$testQuestions = @(
    "What mountain bikes are available?",
    "Show me road bikes under $1000",
    "What accessories do you have for cycling?", 
    "Which helmets are recommended for safety?",
    "What are the most popular bike models?",
    "Show me bikes suitable for beginners",
    "What maintenance products do you sell?",
    "Which bikes are best for commuting?",
    "What colors are available for road bikes?",
    "Do you have electric bikes in stock?"
)

$results = @()
$successCount = 0
$errorCount = 0

Write-Host "`n🧪 Running $TestCount API tests with $DelaySeconds second delays..." -ForegroundColor Yellow

for ($i = 1; $i -le $TestCount; $i++) {
    $question = $testQuestions[($i - 1) % $testQuestions.Count]
    
    Write-Host "`n[$i/$TestCount] Testing: $question" -ForegroundColor White
    
    $body = @{
        queryText = $question
        skill = "Product_azzEXjGzazCl78XgkHBkV"
        options = @("GetResultsSummary")
    } | ConvertTo-Json
    
    $startTime = Get-Date
    
    try {
        $response = Invoke-RestMethod -Uri $apiUrl -Method POST -Headers $headers -Body $body -TimeoutSec 30
        $duration = ((Get-Date) - $startTime).TotalMilliseconds
        
        $successCount++
        Write-Host "   ✅ Success ($([math]::Round($duration))ms)" -ForegroundColor Green
        
        # Analyze response
        $resultInfo = @{
            Question = $question
            Success = $true
            Duration = $duration
            HasResults = $false
            ResultCount = 0
            Error = $null
        }
        
        if ($response -and $response.results) {
            $resultInfo.HasResults = $true
            $resultInfo.ResultCount = $response.results.Count
            Write-Host "   📊 Found $($response.results.Count) results" -ForegroundColor Cyan
        }
        elseif ($response -and $response.summary) {
            Write-Host "   📋 Response includes summary" -ForegroundColor Cyan
        }
        else {
            Write-Host "   ⚠️ Response format unknown" -ForegroundColor Yellow
        }
        
        $results += $resultInfo
    }
    catch {
        $duration = ((Get-Date) - $startTime).TotalMilliseconds
        $errorCount++
        
        Write-Host "   ❌ Error ($([math]::Round($duration))ms)" -ForegroundColor Red
        Write-Host "   📝 $($_.Exception.Message)" -ForegroundColor Red
        
        $statusCode = $null
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
            Write-Host "   🔢 Status: $statusCode" -ForegroundColor Red
        }
        
        $results += @{
            Question = $question
            Success = $false
            Duration = $duration
            HasResults = $false
            ResultCount = 0
            Error = $_.Exception.Message
            StatusCode = $statusCode
        }
    }
    
    # Delay between requests
    if ($i -lt $TestCount) {
        Start-Sleep -Seconds $DelaySeconds
    }
}

# Results summary
Write-Host "`n" -NoNewline
Write-Host "📊 TEST RESULTS SUMMARY" -ForegroundColor Cyan
Write-Host "=" * 30 -ForegroundColor Gray

$successRate = [math]::Round(($successCount / $TestCount) * 100, 1)
Write-Host "✅ Successful: $successCount/$TestCount ($successRate%)" -ForegroundColor Green
Write-Host "❌ Failed: $errorCount/$TestCount ($([math]::Round(($errorCount / $TestCount) * 100, 1))%)" -ForegroundColor Red

# Performance stats
$successfulResults = $results | Where-Object { $_.Success -eq $true }
if ($successfulResults.Count -gt 0) {
    $avgDuration = [math]::Round(($successfulResults | Measure-Object -Property Duration -Average).Average)
    $maxDuration = [math]::Round(($successfulResults | Measure-Object -Property Duration -Maximum).Maximum)
    $minDuration = [math]::Round(($successfulResults | Measure-Object -Property Duration -Minimum).Minimum)
    
    Write-Host "⏱️ Response times: Avg $avgDuration ms, Min $minDuration ms, Max $maxDuration ms" -ForegroundColor White
}

# Data quality stats
$resultsWithData = ($results | Where-Object { $_.HasResults -eq $true }).Count
if ($resultsWithData -gt 0) {
    Write-Host "📊 Responses with data: $resultsWithData/$successCount" -ForegroundColor Cyan
}

# Error analysis
if ($errorCount -gt 0) {
    Write-Host "`n❌ ERROR ANALYSIS:" -ForegroundColor Red
    $errorResults = $results | Where-Object { $_.Success -eq $false }
    $errorGroups = $errorResults | Group-Object -Property Error
    
    foreach ($group in $errorGroups) {
        Write-Host "   $($group.Count)x $($group.Name)" -ForegroundColor Red
    }
}

Write-Host "`n🎯 COMPARISON TO PREVIOUS ISSUES:" -ForegroundColor Yellow
Write-Host "   Previous failure rate: ~33% (from analysis)" -ForegroundColor White
Write-Host "   Current failure rate: $([math]::Round(($errorCount / $TestCount) * 100, 1))%" -ForegroundColor White

if ($errorCount -eq 0) {
    Write-Host "🎉 PERFECT! All tests passed - token and API are working great!" -ForegroundColor Green
    Write-Host "   Ready for full multi-thread runner testing" -ForegroundColor Green
}
elseif ($successRate -gt 90) {
    Write-Host "✅ EXCELLENT! Success rate > 90% - major improvement!" -ForegroundColor Green
}
elseif ($successRate -gt 67) {
    Write-Host "✅ GOOD! Success rate improved from previous 67%" -ForegroundColor Green
}
else {
    Write-Host "⚠️ Still seeing issues - may need further investigation" -ForegroundColor Yellow
}

Write-Host "`n" -NoNewline