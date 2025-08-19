#!/usr/bin/env pwsh
param(
    [Parameter(Mandatory=$true)]
    [string]$Query,
    
    [Parameter()]
    [switch]$ShowDetails,
    
    [Parameter()]
    [switch]$SaveResults
)

<#
.SYNOPSIS
    Compares Agentic Search and Dataverse Search results for a given query

.DESCRIPTION
    This script calls both the Agentic Search API (web app) and Dataverse Search API,
    then displays a comparison of the results.

.PARAMETER Query
    The search query to test with both systems

.PARAMETER ShowDetails
    Show detailed results from both APIs

.PARAMETER SaveResults
    Save results to JSON files for further analysis

.EXAMPLE
    .\Test-SearchComparison.ps1 -Query "gloves under 50"
    
.EXAMPLE
    .\Test-SearchComparison.ps1 -Query "hiking boots" -ShowDetails -SaveResults
#>

# Define API endpoints
$AgenticApiUrl = "https://jiantmo-retail-rag-web-app.azurewebsites.net/agentic/search"
$DataverseScriptPath = ".\Test-DataverseSearch.ps1"

Write-Host "🔍 Search Comparison Test" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Write-Host "Query: '$Query'" -ForegroundColor Yellow
Write-Host ""

# Test 1: Agentic Search API
Write-Host "1️⃣ Testing Agentic Search API..." -ForegroundColor Green
Write-Host "   URL: $AgenticApiUrl" -ForegroundColor Gray

try {
    $agenticStartTime = Get-Date
    
    $agenticBody = @{
        Query = $Query
    } | ConvertTo-Json
    
    $agenticResponse = Invoke-RestMethod -Uri $AgenticApiUrl -Method POST -ContentType "application/json" -Body $agenticBody -TimeoutSec 30
    
    $agenticEndTime = Get-Date
    $agenticDuration = ($agenticEndTime - $agenticStartTime).TotalMilliseconds
    
    Write-Host "   ✅ Success! Response time: $($agenticDuration.ToString('F0'))ms" -ForegroundColor Green
    
    # Parse agentic response
    $agenticProductCount = 0
    $agenticProducts = @()
    
    if ($agenticResponse.result -and $agenticResponse.result.FormattedText) {
        try {
            $formattedText = $agenticResponse.result.FormattedText | ConvertFrom-Json
            if ($formattedText.content_items) {
                $agenticProducts = $formattedText.content_items | Where-Object { $_.ref_id -match "product" }
                $agenticProductCount = $agenticProducts.Count
            }
        } catch {
            Write-Host "   ⚠️ Could not parse FormattedText as JSON" -ForegroundColor Yellow
        }
    }
    
    Write-Host "   📊 Products found: $agenticProductCount" -ForegroundColor Cyan
    
} catch {
    Write-Host "   ❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
    $agenticResponse = $null
    $agenticDuration = 0
    $agenticProductCount = 0
    $agenticProducts = @()
}

Write-Host ""

# Test 2: Dataverse Search API
Write-Host "2️⃣ Testing Dataverse Search API..." -ForegroundColor Green
Write-Host "   Script: $DataverseScriptPath" -ForegroundColor Gray

try {
    $dataverseStartTime = Get-Date
    
    # Check if Test-DataverseSearch.ps1 exists
    if (-not (Test-Path $DataverseScriptPath)) {
        throw "Test-DataverseSearch.ps1 not found in current directory"
    }
    
    # Call Dataverse search script
    $dataverseResult = & $DataverseScriptPath -Query $Query
    
    $dataverseEndTime = Get-Date
    $dataverseDuration = ($dataverseEndTime - $dataverseStartTime).TotalMilliseconds
    
    Write-Host "   ✅ Success! Response time: $($dataverseDuration.ToString('F0'))ms" -ForegroundColor Green
    
    # Parse dataverse response
    $dataverseProductCount = 0
    $dataverseProducts = @()
    
    if ($dataverseResult -and $dataverseResult.queryResult -and $dataverseResult.queryResult.result) {
        $dataverseProducts = $dataverseResult.queryResult.result
        $dataverseProductCount = $dataverseProducts.Count
    }
    
    Write-Host "   📊 Products found: $dataverseProductCount" -ForegroundColor Cyan
    
} catch {
    Write-Host "   ❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
    $dataverseResult = $null
    $dataverseDuration = 0
    $dataverseProductCount = 0
    $dataverseProducts = @()
}

Write-Host ""

# Results Comparison
Write-Host "📊 COMPARISON RESULTS" -ForegroundColor Magenta
Write-Host "=====================" -ForegroundColor Magenta

$comparisonTable = @(
    [PSCustomObject]@{
        Metric = "Response Time (ms)"
        "Agentic Search" = if ($agenticDuration -gt 0) { $agenticDuration.ToString('F0') } else { "Failed" }
        "Dataverse Search" = if ($dataverseDuration -gt 0) { $dataverseDuration.ToString('F0') } else { "Failed" }
        Winner = if ($agenticDuration -gt 0 -and $dataverseDuration -gt 0) {
            if ($agenticDuration -lt $dataverseDuration) { "🏆 Agentic" } else { "🏆 Dataverse" }
        } else { "N/A" }
    },
    [PSCustomObject]@{
        Metric = "Products Found"
        "Agentic Search" = $agenticProductCount
        "Dataverse Search" = $dataverseProductCount
        Winner = if ($agenticProductCount -gt $dataverseProductCount) { "🏆 Agentic" } elseif ($dataverseProductCount -gt $agenticProductCount) { "🏆 Dataverse" } else { "🤝 Tie" }
    },
    [PSCustomObject]@{
        Metric = "API Success"
        "Agentic Search" = if ($agenticResponse) { "✅ Success" } else { "❌ Failed" }
        "Dataverse Search" = if ($dataverseResult) { "✅ Success" } else { "❌ Failed" }
        Winner = if ($agenticResponse -and $dataverseResult) { "🤝 Both" } elseif ($agenticResponse) { "🏆 Agentic" } elseif ($dataverseResult) { "🏆 Dataverse" } else { "❌ Both Failed" }
    }
)

$comparisonTable | Format-Table -AutoSize

# Show detailed results if requested
if ($ShowDetails) {
    Write-Host ""
    Write-Host "🔍 DETAILED RESULTS" -ForegroundColor Yellow
    Write-Host "===================" -ForegroundColor Yellow
    
    if ($agenticResponse) {
        Write-Host ""
        Write-Host "🤖 Agentic Search Details:" -ForegroundColor Green
        if ($agenticProducts.Count -gt 0) {
            $agenticProducts | ForEach-Object {
                $content = $_.content
                if ($content -match 'Name:\s*([^,]+).*?Price:\s*\$?([\d.]+)') {
                    $name = $matches[1].Trim()
                    $price = $matches[2]
                    Write-Host "   • $name - `$$price" -ForegroundColor White
                }
            }
        } else {
            Write-Host "   No products parsed from response" -ForegroundColor Gray
        }
    }
    
    if ($dataverseResult) {
        Write-Host ""
        Write-Host "🏢 Dataverse Search Details:" -ForegroundColor Blue
        if ($dataverseProducts.Count -gt 0) {
            $dataverseProducts | ForEach-Object {
                $name = $_.DisplayName
                $price = $_.cr4a3_price
                Write-Host "   • $name - `$$price" -ForegroundColor White
            }
        } else {
            Write-Host "   No products found" -ForegroundColor Gray
        }
    }
}

# Save results if requested
if ($SaveResults) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $resultsDir = "search_comparison_results"
    
    if (-not (Test-Path $resultsDir)) {
        New-Item -ItemType Directory -Path $resultsDir | Out-Null
    }
    
    Write-Host ""
    Write-Host "💾 Saving Results..." -ForegroundColor Yellow
    
    # Save agentic results
    if ($agenticResponse) {
        $agenticFile = "$resultsDir\agentic_$timestamp.json"
        $agenticResponse | ConvertTo-Json -Depth 10 | Out-File -FilePath $agenticFile -Encoding UTF8
        Write-Host "   Agentic results saved to: $agenticFile" -ForegroundColor Green
    }
    
    # Save dataverse results  
    if ($dataverseResult) {
        $dataverseFile = "$resultsDir\dataverse_$timestamp.json"
        $dataverseResult | ConvertTo-Json -Depth 10 | Out-File -FilePath $dataverseFile -Encoding UTF8
        Write-Host "   Dataverse results saved to: $dataverseFile" -ForegroundColor Blue
    }
    
    # Save comparison summary
    $summaryFile = "$resultsDir\comparison_$timestamp.json"
    $summary = @{
        query = $Query
        timestamp = $timestamp
        agentic = @{
            success = [bool]$agenticResponse
            response_time_ms = $agenticDuration
            product_count = $agenticProductCount
        }
        dataverse = @{
            success = [bool]$dataverseResult
            response_time_ms = $dataverseDuration
            product_count = $dataverseProductCount
        }
        comparison = $comparisonTable
    }
    
    $summary | ConvertTo-Json -Depth 10 | Out-File -FilePath $summaryFile -Encoding UTF8
    Write-Host "   Comparison summary saved to: $summaryFile" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "🎯 Search comparison completed!" -ForegroundColor Green
Write-Host "Query: '$Query'" -ForegroundColor Yellow

# Return results for further processing if needed
return @{
    Query = $Query
    AgenticResponse = $agenticResponse
    DataverseResponse = $dataverseResult
    AgenticDuration = $agenticDuration
    DataverseDuration = $dataverseDuration
    AgenticProductCount = $agenticProductCount
    DataverseProductCount = $dataverseProductCount
}
