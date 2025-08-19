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
    Tests the Agentic Search API with a given query

.DESCRIPTION
    This script calls the Agentic Search API and displays the results.

.PARAMETER Query
    The search query to test

.PARAMETER ShowDetails
    Show detailed product information from the response

.PARAMETER SaveResults
    Save results to a JSON file

.EXAMPLE
    .\Test-AgenticSearch.ps1 -Query "gloves under 50"
    
.EXAMPLE
    .\Test-AgenticSearch.ps1 -Query "hiking boots" -ShowDetails -SaveResults
#>

# Define API endpoint
$AgenticApiUrl = "https://jiantmo-retail-rag-web-app.azurewebsites.net/agentic/search"

Write-Host "🤖 Agentic Search Test" -ForegroundColor Cyan
Write-Host "======================" -ForegroundColor Cyan
Write-Host "Query: '$Query'" -ForegroundColor Yellow
Write-Host "URL: $AgenticApiUrl" -ForegroundColor Gray
Write-Host ""

try {
    $startTime = Get-Date
    
    # Prepare request body
    $requestBody = @{
        Query = $Query
    } | ConvertTo-Json
    
    Write-Host "📡 Sending request..." -ForegroundColor Blue
    
    # Call Agentic Search API
    $response = Invoke-RestMethod -Uri $AgenticApiUrl -Method POST -ContentType "application/json" -Body $requestBody -TimeoutSec 60
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalMilliseconds
    
    Write-Host "✅ Success! Response time: $($duration.ToString('F0'))ms" -ForegroundColor Green
    Write-Host ""
    
    # Parse response
    $productCount = 0
    $products = @()
    
    Write-Host "📊 RESULTS SUMMARY" -ForegroundColor Magenta
    Write-Host "==================" -ForegroundColor Magenta
    Write-Host "Response time: $($duration.ToString('F0'))ms" -ForegroundColor Cyan
    
    # Parse products from new response format
    if ($response.result -and $response.result.Products) {
        $products = $response.result.Products
        $productCount = $products.Count
        
        Write-Host "Products found: $productCount" -ForegroundColor Cyan
        
        # Show summary if available
        if ($response.result.Summary) {
            Write-Host ""
            Write-Host "� Summary:" -ForegroundColor Yellow
            Write-Host $response.result.Summary -ForegroundColor White
        }
        
        # Show explanation if available
        if ($response.result.Explanation) {
            Write-Host ""
            Write-Host "� Explanation:" -ForegroundColor Yellow
            Write-Host $response.result.Explanation -ForegroundColor White
        }
        
        # Show detailed results if requested
        if ($ShowDetails -and $products.Count -gt 0) {
            Write-Host ""
            Write-Host "🔍 PRODUCT DETAILS" -ForegroundColor Yellow
            Write-Host "==================" -ForegroundColor Yellow
            
            $products | ForEach-Object -Begin { $i = 1 } -Process {
                Write-Host ""
                Write-Host "$i. Product:" -ForegroundColor Green
                
                # For new API format, products have direct properties
                if ($_.Name) {
                    Write-Host "   Name: $($_.Name)" -ForegroundColor White
                }
                
                if ($_.Price) {
                    Write-Host "   Price: $($_.Price)" -ForegroundColor White
                }
                
                if ($_.Description) {
                    Write-Host "   Description: $($_.Description)" -ForegroundColor White
                }
                
                # Show any additional properties
                $_.PSObject.Properties | Where-Object { $_.Name -notin @('Name', 'Price', 'Description') } | ForEach-Object {
                    Write-Host "   $($_.Name): $($_.Value)" -ForegroundColor Gray
                }
                
                $i++
            }
        }
    } else {
        Write-Host "Products found: 0" -ForegroundColor Cyan
        Write-Host "⚠️ No Products found in response" -ForegroundColor Yellow
    }
    
    # Save results if requested
    if ($SaveResults) {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $resultsDir = "agentic_search_results"
        
        if (-not (Test-Path $resultsDir)) {
            New-Item -ItemType Directory -Path $resultsDir | Out-Null
        }
        
        Write-Host ""
        Write-Host "💾 Saving Results..." -ForegroundColor Yellow
        
        $resultFile = "$resultsDir\agentic_search_$timestamp.json"
        $resultData = @{
            query = $Query
            timestamp = $timestamp
            response_time_ms = $duration
            product_count = $productCount
            raw_response = $response
            parsed_products = $products
        }
        
        $resultData | ConvertTo-Json -Depth 10 | Out-File -FilePath $resultFile -Encoding UTF8
        Write-Host "Results saved to: $resultFile" -ForegroundColor Green
    }
    
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode
        Write-Host "Status Code: $statusCode" -ForegroundColor Red
        
        if ($_.Exception.Response.Content) {
            Write-Host "Response Content:" -ForegroundColor Red
            Write-Host $_.Exception.Response.Content -ForegroundColor Gray
        }
    }
}

Write-Host ""
Write-Host "🎯 Agentic search test completed!" -ForegroundColor Green
