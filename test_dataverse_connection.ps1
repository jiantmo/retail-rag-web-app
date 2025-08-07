# Test script to validate Dataverse API connectivity
param(
    [string]$TokenFile = "token.config"
)

function Test-ApiConnection {
    param([string]$TokenFile)
    
    Write-Host "🔄 Testing API connection..." -ForegroundColor Yellow
    
    # Load token
    try {
        $token = Get-Content -Path $TokenFile -Raw -ErrorAction Stop
        $token = $token.Trim()
    }
    catch {
        Write-Host "❌ Error: token.config file not found" -ForegroundColor Red
        return $false
    }
    
    # API configuration
    $url = "https://aurorabapenv87b96.crm10.dynamics.com/api/copilot/v1.0/queryskillstructureddata"
    $headers = @{
        "Content-Type" = "application/json"
        "User-Agent" = "insomnia/11.4.0"
        "x-ms-crm-query-language" = "1033"
        "x-ms-crm-service-root-url" = "https://aurorabapenv87b96.crm10.dynamics.com/"
        "x-ms-crm-userid" = "aurorauser01@aurorafinanceintegration02.onmicrosoft.com"
        "x-ms-organization-id" = "440a70c9-ff61-f011-beb8-6045bd09e9cc"
        "x-ms-user-agent" = "PowerVA/2"
        "Authorization" = "Bearer $token"
    }
    
    # Test payload
    $payload = @{
        queryText = "how many glove do I have?"
        skill = "Product_azzEXjGzazCl78XgkHBkV"
        options = @("GetResultsSummary")
        additionalProperties = @{
            ExecuteUnifiedSearch = $true
        }
    } | ConvertTo-Json -Depth 10
    
    Write-Host "📍 URL: $url" -ForegroundColor Gray
    Write-Host "🔑 Token length: $($token.Length) characters" -ForegroundColor Gray
    Write-Host "📝 Test query: how many glove do I have?" -ForegroundColor Gray
    Write-Host ""
    
    try {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $response = Invoke-RestMethod -Uri $url -Method POST -Headers $headers -Body $payload -TimeoutSec 30
        $stopwatch.Stop()
        
        Write-Host "📊 Status Code: 200" -ForegroundColor Green
        Write-Host "⏱️  Response Time: $($stopwatch.Elapsed.TotalSeconds.ToString('F2')) seconds" -ForegroundColor Green
        Write-Host "✅ API call successful!" -ForegroundColor Green
        
        # Parse response
        if ($response) {
            $responseKeys = if ($response -is [PSCustomObject]) { 
                ($response | Get-Member -MemberType NoteProperty).Name -join ", "
            } else { 
                $response.GetType().Name 
            }
            Write-Host "📄 Response structure: $responseKeys" -ForegroundColor Gray
            
            # Save test response
            $response | ConvertTo-Json -Depth 10 | Out-File -FilePath "test_api_response.json" -Encoding UTF8
            Write-Host "💾 Response saved to test_api_response.json" -ForegroundColor Gray
        }
        
        return $true
    }
    catch {
        $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode } else { "Unknown" }
        Write-Host "❌ API call failed!" -ForegroundColor Red
        Write-Host "📊 Status Code: $statusCode" -ForegroundColor Red
        Write-Host "📄 Error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Test-QuestionFiles {
    Write-Host "`n🔍 Checking for question files..." -ForegroundColor Yellow
    
    # Look for JSON files
    $jsonFiles = Get-ChildItem -Path "." -Recurse -Filter "*.json" | Where-Object {
        $_.Name -match "(question|test_case|customer)"
    }
    
    # Look for Markdown files
    $mdFiles = Get-ChildItem -Path "." -Recurse -Filter "*.md" | Where-Object {
        $_.Name -match "(question|customer)"
    }
    
    $allQuestionFiles = @($jsonFiles) + @($mdFiles)
    
    Write-Host "📁 Found $($jsonFiles.Count) JSON question files" -ForegroundColor Gray
    Write-Host "📁 Found $($mdFiles.Count) Markdown question files" -ForegroundColor Gray
    Write-Host "📁 Total question files: $($allQuestionFiles.Count)" -ForegroundColor Cyan
    
    if ($allQuestionFiles.Count -gt 0) {
        Write-Host "`n📋 Question files found:" -ForegroundColor Gray
        $filesToShow = $allQuestionFiles | Select-Object -First 10
        foreach ($file in $filesToShow) {
            $relativePath = $file.FullName.Replace((Get-Location).Path, "").TrimStart('\')
            Write-Host "   • $relativePath" -ForegroundColor Gray
        }
        if ($allQuestionFiles.Count -gt 10) {
            Write-Host "   ... and $($allQuestionFiles.Count - 10) more" -ForegroundColor Gray
        }
    }
    else {
        Write-Host "⚠️  No question files found" -ForegroundColor Yellow
    }
    
    return $allQuestionFiles.Count
}

function Main {
    Write-Host "🚀 Dataverse API Connection Test" -ForegroundColor Cyan
    Write-Host ("=" * 40) -ForegroundColor Cyan
    
    # Test API connection
    $apiSuccess = Test-ApiConnection -TokenFile $TokenFile
    
    # Check for question files
    $fileCount = Test-QuestionFiles
    
    # Summary
    Write-Host ("`n" + ("=" * 40)) -ForegroundColor Cyan
    Write-Host "📊 TEST SUMMARY" -ForegroundColor Cyan
    
    $apiStatus = if ($apiSuccess) { "✅ Success" } else { "❌ Failed" }
    Write-Host "🔗 API Connection: $apiStatus" -ForegroundColor $(if ($apiSuccess) { "Green" } else { "Red" })
    Write-Host "📁 Question Files: $fileCount found" -ForegroundColor Cyan
    
    if ($apiSuccess -and $fileCount -gt 0) {
        Write-Host "🎉 Ready to run multi-threaded search!" -ForegroundColor Green
        Write-Host "`n🏃 Next steps:" -ForegroundColor Yellow
        Write-Host "   Python: python multi_thread_dataverse_search.py" -ForegroundColor Gray
        Write-Host "   PowerShell: .\multi_thread_dataverse_search.ps1" -ForegroundColor Gray
    }
    elseif (-not $apiSuccess) {
        Write-Host "⚠️  Fix API connection before running search" -ForegroundColor Yellow
    }
    elseif ($fileCount -eq 0) {
        Write-Host "⚠️  Add question files before running search" -ForegroundColor Yellow
    }
}

# Run the test
Main
