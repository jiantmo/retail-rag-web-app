# Knowledge Agent权限检查和分配脚本
# 检查Knowledge Agent状态，如果权限不足则分配必要的权限

param(
    [string]$ResourceGroupName = "jiantmo-rg",
    [string]$SearchServiceName = "jiantmo-acs", 
    [string]$AppServiceName = "retail-rag-app",
    [switch]$AssignPermissions = $false,
    [switch]$Force = $false
)

Write-Host "🔍 Knowledge Agent 权限检查开始..." -ForegroundColor Green
Write-Host "📂 资源组: $ResourceGroupName"
Write-Host "🔍 搜索服务: $SearchServiceName"
Write-Host "🌐 应用服务: $AppServiceName"
Write-Host ""

# 检查Azure CLI登录状态
Write-Host "🔐 检查Azure CLI登录状态..." -ForegroundColor Yellow
try {
    $accountInfo = az account show 2>$null | ConvertFrom-Json
    if ($accountInfo) {
        Write-Host "✅ 已登录Azure CLI - 用户: $($accountInfo.user.name)" -ForegroundColor Green
        Write-Host "📋 订阅: $($accountInfo.name) ($($accountInfo.id))" -ForegroundColor Cyan
    } else {
        Write-Host "❌ 未登录Azure CLI，请先运行 'az login'" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Azure CLI未安装或配置错误" -ForegroundColor Red
    exit 1
}

# 获取当前用户的Object ID
Write-Host "`n👤 获取当前用户信息..." -ForegroundColor Yellow
try {
    $currentUser = az ad signed-in-user show | ConvertFrom-Json
    $currentUserObjectId = $currentUser.id
    Write-Host "✅ 当前用户: $($currentUser.displayName) ($($currentUser.userPrincipalName))" -ForegroundColor Green
    Write-Host "🆔 Object ID: $currentUserObjectId" -ForegroundColor Cyan
} catch {
    Write-Host "❌ 无法获取当前用户信息" -ForegroundColor Red
    exit 1
}

# 检查资源组是否存在
Write-Host "`n📦 检查资源组..." -ForegroundColor Yellow
try {
    $rg = az group show --name $ResourceGroupName 2>$null | ConvertFrom-Json
    if ($rg) {
        Write-Host "✅ 找到资源组: $($rg.name) (位置: $($rg.location))" -ForegroundColor Green
    } else {
        Write-Host "❌ 资源组不存在: $ResourceGroupName" -ForegroundColor Red
        Write-Host "💡 请先创建资源组或检查名称是否正确" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ 无法检查资源组" -ForegroundColor Red
    exit 1
}

# 查找搜索服务
Write-Host "`n🔍 查找搜索服务..." -ForegroundColor Yellow
try {
    $searchServices = az search service list --resource-group $ResourceGroupName | ConvertFrom-Json
    $searchService = $searchServices | Where-Object { $_.name -eq $SearchServiceName }
    
    if (-not $searchService) {
        # 如果没有找到指定名称的服务，列出所有可用的搜索服务
        if ($searchServices.Count -gt 0) {
            Write-Host "⚠️ 未找到指定的搜索服务: $SearchServiceName" -ForegroundColor Yellow
            Write-Host "📋 可用的搜索服务:" -ForegroundColor Cyan
            foreach ($service in $searchServices) {
                Write-Host "   - $($service.name) (SKU: $($service.sku.name))" -ForegroundColor White
            }
            # 使用第一个搜索服务
            $searchService = $searchServices[0]
            $SearchServiceName = $searchService.name
            Write-Host "🔄 使用搜索服务: $SearchServiceName" -ForegroundColor Yellow
        } else {
            Write-Host "❌ 在资源组中没有找到任何搜索服务" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "✅ 找到搜索服务: $($searchService.name)" -ForegroundColor Green
    }
    
    Write-Host "🔍 搜索服务详情:" -ForegroundColor Cyan
    Write-Host "   - 名称: $($searchService.name)"
    Write-Host "   - SKU: $($searchService.sku.name)"
    Write-Host "   - 状态: $($searchService.status)"
    Write-Host "   - 端点: https://$($searchService.name).search.windows.net/"
} catch {
    Write-Host "❌ 无法查找搜索服务" -ForegroundColor Red
    exit 1
}

# 查找应用服务
Write-Host "`n🌐 查找应用服务..." -ForegroundColor Yellow
try {
    $webApps = az webapp list --resource-group $ResourceGroupName | ConvertFrom-Json
    $webApp = $webApps | Where-Object { $_.name -eq $AppServiceName }
    
    if (-not $webApp) {
        if ($webApps.Count -gt 0) {
            Write-Host "⚠️ 未找到指定的应用服务: $AppServiceName" -ForegroundColor Yellow
            Write-Host "📋 可用的应用服务:" -ForegroundColor Cyan
            foreach ($app in $webApps) {
                Write-Host "   - $($app.name) (状态: $($app.state))" -ForegroundColor White
            }
            # 使用第一个应用服务
            $webApp = $webApps[0]
            $AppServiceName = $webApp.name
            Write-Host "🔄 使用应用服务: $AppServiceName" -ForegroundColor Yellow
        } else {
            Write-Host "⚠️ 在资源组中没有找到任何应用服务" -ForegroundColor Yellow
            Write-Host "💡 应用服务可能还未创建，这是正常的" -ForegroundColor Cyan
            $webApp = $null
        }
    } else {
        Write-Host "✅ 找到应用服务: $($webApp.name)" -ForegroundColor Green
        Write-Host "🌐 应用服务详情:" -ForegroundColor Cyan
        Write-Host "   - 名称: $($webApp.name)"
        Write-Host "   - 状态: $($webApp.state)"
        Write-Host "   - URL: https://$($webApp.defaultHostName)"
    }
} catch {
    Write-Host "❌ 无法查找应用服务" -ForegroundColor Red
    $webApp = $null
}

# 检查当前用户对搜索服务的权限
Write-Host "`n🔐 检查搜索服务权限..." -ForegroundColor Yellow
try {
    $searchResourceId = "/subscriptions/$($accountInfo.id)/resourceGroups/$ResourceGroupName/providers/Microsoft.Search/searchServices/$SearchServiceName"
    
    # 检查角色分配
    $roleAssignments = az role assignment list --assignee $currentUserObjectId --scope $searchResourceId | ConvertFrom-Json
    
    Write-Host "📋 当前角色分配:" -ForegroundColor Cyan
    if ($roleAssignments.Count -eq 0) {
        Write-Host "   ❌ 没有找到任何角色分配" -ForegroundColor Red
        $needsPermissions = $true
    } else {
        $needsPermissions = $false
        foreach ($assignment in $roleAssignments) {
            Write-Host "   ✅ $($assignment.roleDefinitionName)" -ForegroundColor Green
            
            # 检查是否有必要的权限
            if ($assignment.roleDefinitionName -in @("Search Service Contributor", "Search Index Data Contributor", "Cognitive Services OpenAI Contributor", "Owner", "Contributor")) {
                $needsPermissions = $false
            }
        }
    }
    
    # 检查Knowledge Agent功能需要的具体权限
    $requiredRoles = @(
        "Search Service Contributor",
        "Search Index Data Contributor", 
        "Cognitive Services OpenAI Contributor"
    )
    
    Write-Host "`n🎯 Knowledge Agent 所需权限:" -ForegroundColor Yellow
    foreach ($role in $requiredRoles) {
        $hasRole = $roleAssignments | Where-Object { $_.roleDefinitionName -eq $role }
        if ($hasRole) {
            Write-Host "   ✅ $role" -ForegroundColor Green
        } else {
            Write-Host "   ❌ $role (缺失)" -ForegroundColor Red
            $needsPermissions = $true
        }
    }
    
} catch {
    Write-Host "❌ 无法检查权限" -ForegroundColor Red
    $needsPermissions = $true
}

# 检查Knowledge Agent状态 (通过API)
Write-Host "`n🤖 检查Knowledge Agent状态..." -ForegroundColor Yellow
try {
    # 如果应用正在运行，尝试调用status API
    if ($webApp -and $webApp.state -eq "Running") {
        $statusUrl = "https://$($webApp.defaultHostName)/KnowledgeAgent/status"
        Write-Host "🌐 调用API: $statusUrl" -ForegroundColor Cyan
        
        try {
            $response = Invoke-RestMethod -Uri $statusUrl -Method GET -TimeoutSec 30
            if ($response.success -eq $true) {
                Write-Host "✅ Knowledge Agent 状态: $($response.status)" -ForegroundColor Green
                Write-Host "📝 消息: $($response.message)" -ForegroundColor White
                if ($response.agentName) {
                    Write-Host "🏷️ Agent名称: $($response.agentName)" -ForegroundColor Cyan
                }
            } else {
                Write-Host "⚠️ Knowledge Agent 状态: $($response.status)" -ForegroundColor Yellow
                Write-Host "📝 消息: $($response.message)" -ForegroundColor White
            }
        } catch {
            Write-Host "⚠️ 无法连接到Knowledge Agent API" -ForegroundColor Yellow
            Write-Host "💡 这可能是因为应用未部署或正在启动中" -ForegroundColor Cyan
        }
    } else {
        Write-Host "⚠️ 应用服务未运行，无法检查Knowledge Agent状态" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️ 无法检查Knowledge Agent状态" -ForegroundColor Yellow
}

# 权限分配
if ($needsPermissions) {
    Write-Host "`n⚠️ 检测到权限不足!" -ForegroundColor Yellow
    
    if ($AssignPermissions -or $Force) {
        Write-Host "🔧 开始分配必要的权限..." -ForegroundColor Green
        
        foreach ($role in $requiredRoles) {
            try {
                Write-Host "🔐 分配角色: $role" -ForegroundColor Yellow
                $result = az role assignment create `
                    --assignee $currentUserObjectId `
                    --role $role `
                    --scope $searchResourceId | ConvertFrom-Json
                
                if ($result) {
                    Write-Host "   ✅ 成功分配: $role" -ForegroundColor Green
                } else {
                    Write-Host "   ⚠️ 角色可能已存在: $role" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "   ❌ 分配失败: $role - $($_.Exception.Message)" -ForegroundColor Red
            }
        }
        
        Write-Host "`n⏳ 权限分配完成，等待传播..." -ForegroundColor Yellow
        Write-Host "💡 权限传播通常需要几分钟时间生效" -ForegroundColor Cyan
        
    } else {
        Write-Host "💡 运行以下命令分配权限:" -ForegroundColor Cyan
        Write-Host "   .\verify-permissions.ps1 -ResourceGroupName `"$ResourceGroupName`" -SearchServiceName `"$SearchServiceName`" -AssignPermissions" -ForegroundColor White
    }
} else {
    Write-Host "`n✅ 权限检查通过!" -ForegroundColor Green
}

# 输出总结
Write-Host "`n📊 检查总结:" -ForegroundColor Green
Write-Host "├─ 资源组: $(if($rg) {'✅'} else {'❌'}) $ResourceGroupName"
Write-Host "├─ 搜索服务: $(if($searchService) {'✅'} else {'❌'}) $SearchServiceName"
Write-Host "├─ 应用服务: $(if($webApp) {'✅'} else {'⚠️'}) $AppServiceName"
Write-Host "├─ 用户权限: $(if(-not $needsPermissions) {'✅'} else {'❌'}) Knowledge Agent权限"
Write-Host "└─ 整体状态: $(if($rg -and $searchService -and -not $needsPermissions) {'🟢 就绪'} else {'🟡 需要配置'})"

if ($needsPermissions -and -not $AssignPermissions) {
    Write-Host "`n🚀 下一步操作:" -ForegroundColor Yellow
    Write-Host "1. 运行权限分配: .\check-knowledge-agent.ps1 -AssignPermissions" -ForegroundColor White
    Write-Host "2. 等待权限传播 (2-5分钟)" -ForegroundColor White
    Write-Host "3. 重新运行检查: .\check-knowledge-agent.ps1" -ForegroundColor White
}

Write-Host "`n🏁 检查完成!" -ForegroundColor Green
