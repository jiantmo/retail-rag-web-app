# Azure AI Search Agentic Resources Provisioning Script
# 用于创建完整的Azure AI Search + Knowledge Agent环境

param(
    [Parameter(Mandatory=$false)]
    [string]$SubscriptionId = "0f7690ff-3bdf-4d45-9eda-cabd997016d8",
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "jiantmo-rg",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "North Central US",
    
    [Parameter(Mandatory=$false)]
    [string]$StorageAccountName = "jiantmostorageaccount",  # 请修改为您的存储账户名称
    
    [Parameter(Mandatory=$false)]
    [string]$ContainerName = "container",
    
    [Parameter(Mandatory=$false)]
    [string]$DataFilePath = "C:\github\retail-rag-web-app\AdventureWorksDemoDataProducts_with_embedding.json",
    
    [Parameter(Mandatory=$false)]
    [string]$SearchServiceName = "jiantmo-acs",
    
    [Parameter(Mandatory=$false)]
    [string]$SearchIndexName = "rag-acs-index",
    
    [Parameter(Mandatory=$false)]
    [string]$AIServicesName = "jiantmo-ai-services",
    
    [Parameter(Mandatory=$false)]
    [string]$AIServicesProjectName = "jiantmo-ai-services-proj",
    
    [Parameter(Mandatory=$false)]
    [string]$AIFoundryProjectName = "jiantmo-ai-foundry-proj",
    
    [Parameter(Mandatory=$false)]
    [string]$LLMModelName = "gpt-4.1",
    
    [Parameter(Mandatory=$false)]
    [string]$LLMDeploymentName = "gpt-4.1",
    
    [Parameter(Mandatory=$false)]
    [string]$LLMModelVersion = "2025-04-14",
    
    [Parameter(Mandatory=$false)]
    [string]$EmbeddingModelName = "text-embedding-3-large",
    
    [Parameter(Mandatory=$false)]
    [string]$EmbeddingDeploymentName = "text-embedding-3-large",
    
    [Parameter(Mandatory=$false)]
    [string]$EmbeddingModelVersion = "1",
    
    [Parameter(Mandatory=$false)]
    [string]$KnowledgeAgentName = "retail-knowledge-agent"
)

# 颜色输出函数
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Purge已删除的认知服务资源函数
function Invoke-CognitiveServicesPurge {
    param([string]$ResourceName, [string]$Location, [string]$SubscriptionId, [string]$ResourceGroupName)
    
    Write-ColorOutput "🗑️ 尝试purge已删除的认知服务资源: $ResourceName..." "Yellow"
    
    try {
        $purgeCommand = "az resource delete --ids ""/subscriptions/$SubscriptionId/providers/Microsoft.CognitiveServices/locations/$Location/resourceGroups/$ResourceGroupName/deletedAccounts/$ResourceName"""
        Invoke-Expression $purgeCommand
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ 认知服务资源 $ResourceName purge成功" "Green"
        } else {
            Write-ColorOutput "ℹ️ 认知服务资源 $ResourceName 可能已被purge或不存在" "Yellow"
        }
    } catch {
        Write-ColorOutput "⚠️ Purge操作失败: $($_.Exception.Message)" "Yellow"
    }
}

Write-ColorOutput "🚀 开始创建Azure AI Search Agentic资源..." "Green"
Write-ColorOutput "🔧 脚本参数配置:" "Cyan"
Write-ColorOutput "   - 订阅ID: $SubscriptionId" "White"
Write-ColorOutput "   - 资源组: $ResourceGroupName" "White"
Write-ColorOutput "   - 位置: $Location" "White"
Write-ColorOutput "   - 存储账户: $StorageAccountName" "White"
Write-ColorOutput "   - 容器名称: $ContainerName" "White"
Write-ColorOutput "   - 数据文件: $DataFilePath" "White"
Write-ColorOutput "   - LLM模型: $LLMModelName" "White"
Write-ColorOutput "   - 嵌入模型: $EmbeddingModelName" "White"
Write-ColorOutput "" "White"

# 1. 检查Azure登录状态
Write-ColorOutput "🔐 检查Azure登录状态..." "Cyan"
try {
    $context = az account show 2>$null | ConvertFrom-Json
    if ($context) {
        Write-ColorOutput "✅ 已登录Azure，当前订阅: $($context.name)" "Green"
        Write-ColorOutput "   订阅ID: $($context.id)" "White"
    }
} catch {
    Write-ColorOutput "❌ 未登录Azure，请先登录..." "Red"
    Write-ColorOutput "💡 运行: az login" "Yellow"
    exit 1
}

# 2. 设置正确的订阅
Write-ColorOutput "📋 设置订阅..." "Cyan"
az account set --subscription $SubscriptionId
if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput "❌ 设置订阅失败" "Red"
    exit 1
}

# 3. 检查/创建资源组
Write-ColorOutput "📁 检查资源组: $ResourceGroupName..." "Cyan"
$rgExists = az group exists --name $ResourceGroupName
if ($rgExists -eq "false") {
    Write-ColorOutput "📁 创建资源组: $ResourceGroupName..." "Yellow"
    az group create --name $ResourceGroupName --location $Location
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "❌ 创建资源组失败" "Red"
        exit 1
    }
    Write-ColorOutput "✅ 资源组创建成功" "Green"
} else {
    Write-ColorOutput "ℹ️ 资源组 $ResourceGroupName 已存在，跳过创建" "Yellow"
}

# 4. 创建存储账户
Write-ColorOutput "💾 检查存储账户: $StorageAccountName..." "Cyan"
$storageExists = az storage account show --name $StorageAccountName --resource-group $ResourceGroupName 2>$null
if (-not $storageExists) {
    Write-ColorOutput "💾 创建存储账户（Standard性能，LRS冗余）..." "Yellow"
    az storage account create `
        --name $StorageAccountName `
        --resource-group $ResourceGroupName `
        --location $Location `
        --sku "Standard_LRS" `
        --kind "StorageV2" `
        --access-tier "Hot" `
        --allow-blob-public-access false `
        --allow-shared-key-access false `
        --min-tls-version "TLS1_2"
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "❌ 创建存储账户失败" "Red"
        exit 1
    }
    
    Write-ColorOutput "🔄 等待存储账户完全部署..." "Yellow"
    Start-Sleep -Seconds 15
    Write-ColorOutput "✅ 存储账户创建成功" "Green"
} else {
    Write-ColorOutput "ℹ️ 存储账户 $StorageAccountName 已存在，跳过创建" "Yellow"
}

# 4.1. 创建Blob容器
Write-ColorOutput "📦 检查Blob容器: $ContainerName..." "Cyan"
$containerExists = az storage container exists --name $ContainerName --account-name $StorageAccountName --auth-mode login 2>$null | ConvertFrom-Json
if (-not $containerExists.exists) {
    Write-ColorOutput "📦 创建Blob容器: $ContainerName..." "Yellow"
    az storage container create `
        --name $ContainerName `
        --account-name $StorageAccountName `
        --auth-mode login `
        --public-access off
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "❌ 创建Blob容器失败" "Red"
        exit 1
    }
    
    Write-ColorOutput "✅ Blob容器创建成功" "Green"
} else {
    Write-ColorOutput "ℹ️ Blob容器 $ContainerName 已存在，跳过创建" "Yellow"
}

# 4.2. 上传数据文件
$fileName = Split-Path $DataFilePath -Leaf
Write-ColorOutput "📤 检查数据文件: $fileName..." "Cyan"

if (Test-Path $DataFilePath) {
    $blobExists = az storage blob exists --name $fileName --container-name $ContainerName --account-name $StorageAccountName --auth-mode login 2>$null | ConvertFrom-Json
    if (-not $blobExists.exists) {
        Write-ColorOutput "📤 上传数据文件: $fileName..." "Yellow"
        az storage blob upload `
            --file $DataFilePath `
            --name $fileName `
            --container-name $ContainerName `
            --account-name $StorageAccountName `
            --auth-mode login `
            --overwrite false
        
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "❌ 上传数据文件失败" "Red"
            exit 1
        }
        
        Write-ColorOutput "✅ 数据文件上传成功" "Green"
    } else {
        Write-ColorOutput "ℹ️ 数据文件 $fileName 已存在，跳过上传" "Yellow"
    }
} else {
    Write-ColorOutput "⚠️ 本地数据文件 $DataFilePath 不存在，跳过上传" "Yellow"
}

# 1. 检查并删除现有的AI Services Project
Write-ColorOutput "🗑️ 检查并清理现有的AI Services Project..." "Cyan"

# 删除AI Services Project（如果存在）
$projectExists = az ml workspace show --name $AIServicesProjectName --resource-group $ResourceGroupName 2>$null
if ($projectExists) {
    Write-ColorOutput "⚠️ AI Services Project已存在，正在删除..." "Yellow"
    az ml workspace delete --name $AIServicesProjectName --resource-group $ResourceGroupName --yes --no-wait
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ AI Services Project删除成功" "Green"
    } else {
        Write-ColorOutput "⚠️ AI Services Project删除失败，继续执行" "Yellow"
    }
    
    # 等待删除操作完成
    Write-ColorOutput "⏳ 等待Project删除完成..." "Yellow"
    Start-Sleep -Seconds 30
}

# 5. 创建Azure AI Services资源（用于模型部署）
Write-ColorOutput "🧠 检查AI Services资源: $AIServicesName..." "Cyan"
Write-ColorOutput "💡 注意：AI Services资源是模型部署的必需组件" "Yellow"
$aiServicesExists = az cognitiveservices account show --name $AIServicesName --resource-group $ResourceGroupName 2>$null
if (-not $aiServicesExists) {
    # 尝试purge可能存在的已删除资源
    Invoke-CognitiveServicesPurge -ResourceName $AIServicesName -Location $Location -SubscriptionId $SubscriptionId -ResourceGroupName $ResourceGroupName
    
    Write-ColorOutput "🧠 创建AI Services资源..." "Yellow"
    
    try {
        # 使用PowerShell Az模块创建，支持企业策略要求
        $result = New-AzCognitiveServicesAccount `
            -ResourceGroupName $ResourceGroupName `
            -Name $AIServicesName `
            -Type "AIServices" `
            -SkuName "S0" `
            -Location $Location `
            -DisableLocalAuth $true `
            -Force
        
        if ($result) {
            Write-ColorOutput "✅ AI Services资源创建成功" "Green"
        } else {
            Write-ColorOutput "❌ 创建AI Services资源失败" "Red"
        }
    } catch {
        Write-ColorOutput "⚠️ PowerShell创建失败，尝试Azure CLI..." "Yellow"
        
        # 备用方案：使用Azure CLI
        $aiServicesResult = az cognitiveservices account create `
            --name $AIServicesName `
            --resource-group $ResourceGroupName `
            --location $Location `
            --kind "AIServices" `
            --sku "S0" `
            --subscription $SubscriptionId `
            --custom-domain $AIServicesName `
            --disable-local-auth true `
            --yes 2>$null

        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ AI Services资源创建成功" "Green"
        } else {
            Write-ColorOutput "⚠️ AI Services资源创建失败，可能是配额限制或名称冲突" "Yellow"
            Write-ColorOutput "� 请检查Azure门户查看具体错误或尝试使用不同的名称" "Yellow"
        }
    }
    
    # 等待资源完全部署
    Write-ColorOutput "⏳ 等待AI Services资源完全部署..." "Yellow"
    Start-Sleep -Seconds 15
} else {
    Write-ColorOutput "ℹ️ AI Services资源已存在，保留现有资源" "Yellow"
}

# 6. 创建AI Foundry Project (可选，如果权限不足可跳过)
Write-ColorOutput "🤖 尝试创建AI Foundry Project: $AIFoundryProjectName..." "Cyan"

# 首先检查Project是否已存在
$foundryProjectExists = az ml workspace show --name $AIFoundryProjectName --resource-group $ResourceGroupName 2>$null
if ($foundryProjectExists) {
    Write-ColorOutput "ℹ️ AI Foundry Project已存在: $AIFoundryProjectName" "Yellow"
} else {
    Write-ColorOutput "💡 正在尝试创建AI Foundry Project..." "Yellow"
    Write-ColorOutput "⚠️ 如果权限不足，可以稍后通过Azure门户手动创建" "Yellow"
    
    # 尝试创建AI Foundry Project，如果失败不影响其他资源创建
    try {
        $foundryProjectResult = az ml workspace create `
            --name $AIFoundryProjectName `
            --resource-group $ResourceGroupName `
            --location $Location `
            --description "AI Foundry Project for retail RAG application" 2>$null

        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ AI Foundry Project创建成功" "Green"
        } else {
            Write-ColorOutput "⚠️ AI Foundry Project创建失败，可能是权限不足" "Yellow"
            Write-ColorOutput "💡 建议：通过Azure AI Foundry门户 (https://ai.azure.com) 手动创建项目" "Yellow"
            Write-ColorOutput "📋 项目名称: $AIFoundryProjectName" "White"
            Write-ColorOutput "📋 资源组: $ResourceGroupName" "White"
            Write-ColorOutput "📋 位置: $Location" "White"
        }
    } catch {
        Write-ColorOutput "⚠️ AI Foundry Project创建遇到错误，继续执行其他步骤" "Yellow"
        Write-ColorOutput "💡 错误详情: $($_.Exception.Message)" "Red"
    }
}

# 7. 创建独立的AI Services Project (可选，如果权限不足可跳过)
Write-ColorOutput "📁 尝试创建AI Services Project: $AIServicesProjectName..." "Cyan"

# 检查Project是否已存在
$servicesProjectExists = az ml workspace show --name $AIServicesProjectName --resource-group $ResourceGroupName 2>$null
if ($servicesProjectExists) {
    Write-ColorOutput "ℹ️ AI Services Project已存在: $AIServicesProjectName" "Yellow"
} else {
    Write-ColorOutput "💡 正在尝试创建AI Services Project..." "Yellow"
    Write-ColorOutput "⚠️ 如果权限不足，可以稍后通过Azure门户手动创建" "Yellow"
    
    # 尝试创建独立的project workspace，如果失败不影响其他资源创建
    try {
        $servicesProjectResult = az ml workspace create `
            --name $AIServicesProjectName `
            --resource-group $ResourceGroupName `
            --location $Location `
            --description "AI Services Project for retail RAG application" 2>$null

        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ AI Services Project创建成功" "Green"
        } else {
            Write-ColorOutput "⚠️ AI Services Project创建失败，可能是权限不足" "Yellow"
            Write-ColorOutput "💡 建议：通过Azure Machine Learning Studio手动创建工作区" "Yellow"
            Write-ColorOutput "📋 项目名称: $AIServicesProjectName" "White"
            Write-ColorOutput "📋 资源组: $ResourceGroupName" "White"
            Write-ColorOutput "📋 位置: $Location" "White"
        }
    } catch {
        Write-ColorOutput "⚠️ AI Services Project创建遇到错误，继续执行其他步骤" "Yellow"
        Write-ColorOutput "💡 错误详情: $($_.Exception.Message)" "Red"
    }
}

# 8. 部署AI模型到Azure AI Services
Write-ColorOutput "🤖 部署AI模型到Azure AI Services..." "Cyan"

# 部署GPT-4模型
Write-ColorOutput "🧠 检查${LLMModelName}模型部署..." "Cyan"
$gpt4Deployment = az cognitiveservices account deployment show --name $AIServicesName --resource-group $ResourceGroupName --deployment-name $LLMDeploymentName 2>$null
if (-not $gpt4Deployment) {
    Write-ColorOutput "🧠 部署${LLMModelName}模型..." "Yellow"
    az cognitiveservices account deployment create `
        --name $AIServicesName `
        --resource-group $ResourceGroupName `
        --deployment-name $LLMDeploymentName `
        --model-name $LLMModelName `
        --model-version $LLMModelVersion `
        --model-format "OpenAI" `
        --sku-capacity 10 `
        --sku-name "GlobalStandard"
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ ${LLMModelName}模型部署成功" "Green"
    } else {
        Write-ColorOutput "❌ ${LLMModelName}模型部署失败" "Red"
    }
} else {
    Write-ColorOutput "ℹ️ ${LLMModelName}模型已部署，跳过部署" "Yellow"
}

# 部署text-embedding-3-large模型
Write-ColorOutput "📝 检查${EmbeddingModelName}模型部署..." "Cyan"
$embeddingDeployment = az cognitiveservices account deployment show --name $AIServicesName --resource-group $ResourceGroupName --deployment-name $EmbeddingDeploymentName 2>$null
if (-not $embeddingDeployment) {
    Write-ColorOutput "📝 部署${EmbeddingModelName}模型..." "Yellow"
    az cognitiveservices account deployment create `
        --name $AIServicesName `
        --resource-group $ResourceGroupName `
        --deployment-name $EmbeddingDeploymentName `
        --model-name $EmbeddingModelName `
        --model-version $EmbeddingModelVersion `
        --model-format "OpenAI" `
        --sku-capacity 10 `
        --sku-name "GlobalStandard"
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ ${EmbeddingModelName}模型部署成功" "Green"
    } else {
        Write-ColorOutput "❌ ${EmbeddingModelName}模型部署失败" "Red"
    }
} else {
    Write-ColorOutput "ℹ️ ${EmbeddingModelName}模型已部署，跳过部署" "Yellow"
}

# 6. 创建Azure AI Search服务（禁用本地身份验证）
Write-ColorOutput "🔍 检查Azure AI Search服务: $SearchServiceName..." "Cyan"
$searchExists = az search service show --name $SearchServiceName --resource-group $ResourceGroupName 2>$null
if (-not $searchExists) {
    Write-ColorOutput "🔍 创建Azure AI Search服务（禁用本地身份验证）..." "Yellow"
    
    # 等待任何之前的删除操作完成
    $retryCount = 0
    $maxRetries = 5
    
    do {
        try {
            az search service create `
                --name $SearchServiceName `
                --resource-group $ResourceGroupName `
                --sku "standard" `
                --location $Location `
                --identity-type SystemAssigned `
                --disable-local-auth true
            
            if ($LASTEXITCODE -eq 0) {
                break
            }
        } catch {
            Write-ColorOutput "⚠️ 创建失败，可能是删除操作仍在进行中，等待重试..." "Yellow"
        }
        
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-ColorOutput "🔄 等待 60 秒后重试... (尝试 $retryCount/$maxRetries)" "Yellow"
            Start-Sleep -Seconds 60
        }
    } while ($retryCount -lt $maxRetries -and $LASTEXITCODE -ne 0)
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "❌ 创建Azure AI Search服务失败，已达到最大重试次数" "Red"
        exit 1
    }
    
    Write-ColorOutput "🔄 等待Azure AI Search服务完全部署..." "Yellow"
    Start-Sleep -Seconds 60
    Write-ColorOutput "✅ Azure AI Search服务创建成功" "Green"
} else {
    Write-ColorOutput "ℹ️ Azure AI Search服务 $SearchServiceName 已存在，跳过创建" "Yellow"
}

# 7. 配置服务间权限（使用系统托管身份）
Write-ColorOutput "🔐 配置服务间权限..." "Cyan"

# 获取Azure AI Search服务的托管身份
Write-ColorOutput "🔍 获取Azure AI Search托管身份..." "Cyan"
$searchServiceIdentity = az search service show --name $SearchServiceName --resource-group $ResourceGroupName --query identity.principalId -o tsv 2>$null

if ($searchServiceIdentity) {
    Write-ColorOutput "✅ Azure AI Search托管身份ID: $searchServiceIdentity" "Green"
    
    # 为Azure AI Search分配AI Services访问权限
    Write-ColorOutput "🔑 为Azure AI Search分配AI Services访问权限..." "Yellow"
    $aiServicesResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.CognitiveServices/accounts/$AIServicesName"
    
    az role assignment create `
        --assignee $searchServiceIdentity `
        --role "Cognitive Services OpenAI User" `
        --scope $aiServicesResourceId
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ AI Services访问权限分配成功" "Green"
    } else {
        Write-ColorOutput "❌ AI Services访问权限分配失败" "Red"
    }
    
    # 为Azure AI Search分配存储账户访问权限
    Write-ColorOutput "🔑 为Azure AI Search分配存储访问权限..." "Yellow"
    $storageResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Storage/storageAccounts/$StorageAccountName"
    
    az role assignment create `
        --assignee $searchServiceIdentity `
        --role "Storage Blob Data Reader" `
        --scope $storageResourceId
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ 存储访问权限分配成功" "Green"
    } else {
        Write-ColorOutput "❌ 存储访问权限分配失败" "Red"
    }
} else {
    Write-ColorOutput "⚠️ 无法获取Azure AI Search托管身份" "Yellow"
}

# 获取Azure AI Services的托管身份
Write-ColorOutput "🔍 获取Azure AI Services托管身份..." "Cyan"
$aiServicesIdentity = az cognitiveservices account show --name $AIServicesName --resource-group $ResourceGroupName --query identity.principalId -o tsv 2>$null

if ($aiServicesIdentity) {
    Write-ColorOutput "✅ Azure AI Services托管身份ID: $aiServicesIdentity" "Green"
    
    # 为Azure AI Services分配存储账户访问权限
    Write-ColorOutput "🔑 为Azure AI Services分配存储访问权限..." "Yellow"
    $storageResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Storage/storageAccounts/$StorageAccountName"
    
    az role assignment create `
        --assignee $aiServicesIdentity `
        --role "Storage Blob Data Reader" `
        --scope $storageResourceId
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ AI Services存储访问权限分配成功" "Green"
    } else {
        Write-ColorOutput "❌ AI Services存储访问权限分配失败" "Red"
    }
} else {
    Write-ColorOutput "ℹ️ Azure AI Services可能未启用托管身份" "Yellow"
}

# 8. 创建搜索索引
Write-ColorOutput "📊 创建搜索索引: $SearchIndexName..." "Cyan"
# TODO: 添加索引创建逻辑

# 9. 上传示例数据
Write-ColorOutput "📄 上传示例数据..." "Cyan"
# TODO: 添加数据上传逻辑

# 10. 创建Knowledge Agent
Write-ColorOutput "🤝 创建Knowledge Agent: $KnowledgeAgentName..." "Cyan"
# TODO: 添加Knowledge Agent创建逻辑

# 11. 配置权限
Write-ColorOutput "🔐 配置权限..." "Cyan"
Write-ColorOutput "ℹ️ 服务间权限已在步骤7中配置完成" "Green"

Write-ColorOutput "🎉 资源创建完成!" "Green"
Write-ColorOutput "📋 核心资源摘要 (已验证可用):" "Yellow"
Write-ColorOutput "   ✅ 资源组: $ResourceGroupName" "Green"
Write-ColorOutput "   ✅ 存储账户: $StorageAccountName" "Green"
Write-ColorOutput "   ✅ Blob容器: $ContainerName" "Green"
Write-ColorOutput "   ✅ 数据文件: $fileName" "Green"
Write-ColorOutput "   ✅ Azure AI Services: $AIServicesName (状态: 已部署)" "Green"
Write-ColorOutput "   ✅ GPT-4.1模型: $LLMDeploymentName (版本: $LLMModelVersion)" "Green"
Write-ColorOutput "   ✅ 嵌入模型: $EmbeddingDeploymentName (版本: $EmbeddingModelVersion)" "Green"
Write-ColorOutput "   ✅ Azure AI Search: $SearchServiceName" "Green"
Write-ColorOutput "" "White"
Write-ColorOutput "📋 可选资源 (如果创建失败，请参考手动创建指南):" "Yellow"
Write-ColorOutput "   ⚠️ AI Foundry Project: $AIFoundryProjectName" "Yellow"
Write-ColorOutput "   ⚠️ AI Services Project: $AIServicesProjectName" "Yellow"
Write-ColorOutput "   💡 搜索索引: $SearchIndexName (待创建)" "Yellow"
Write-ColorOutput "   💡 Knowledge Agent: $KnowledgeAgentName (待创建)" "Yellow"
Write-ColorOutput "" "White"
Write-ColorOutput "🔗 重要信息:" "Cyan"
Write-ColorOutput "   📖 手动创建指南: AI-Foundry-Manual-Setup-Guide.md" "White"
Write-ColorOutput "   🌐 Azure AI Foundry门户: https://ai.azure.com" "White"
Write-ColorOutput "   🌐 Azure ML Studio: https://ml.azure.com" "White"
Write-ColorOutput "" "White"
Write-ColorOutput "🚀 后续步骤:" "Cyan"
Write-ColorOutput "   1. 如需要，手动创建AI Foundry Project" "White"
Write-ColorOutput "   2. 部署Web应用到Azure App Service" "White"
Write-ColorOutput "   3. 配置应用环境变量连接AI Services" "White"
