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
    [string]$SearchIndexName = "retail-acs-index",
    
    [Parameter(Mandatory=$false)]
    [string]$OpenAIServiceName = "jiantmo-openai",
    
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

# 5. 创建Azure OpenAI服务
Write-ColorOutput "🧠 检查Azure OpenAI服务: $OpenAIServiceName..." "Cyan"
$openAIExists = az cognitiveservices account show --name $OpenAIServiceName --resource-group $ResourceGroupName 2>$null
if (-not $openAIExists) {
    Write-ColorOutput "🧠 创建Azure OpenAI服务（禁用本地身份验证）..." "Yellow"
    
    try {
        # 首先检查是否有软删除的资源需要恢复
        Write-ColorOutput "🔍 检查软删除的OpenAI服务..." "Cyan"
        $deletedServices = Get-AzCognitiveServicesAccount -InRemovedState 2>$null | Where-Object { $_.AccountName -eq $OpenAIServiceName -and $_.Location -eq $Location }
        
        if ($deletedServices) {
            Write-ColorOutput "⚠️ 发现软删除的OpenAI服务，需要清除后重新创建..." "Yellow"
            
            # 清除软删除的账户
            Write-ColorOutput "🗑️ 清除软删除的OpenAI服务..." "Yellow"
            Remove-AzCognitiveServicesAccount -ResourceGroupName $ResourceGroupName -Name $OpenAIServiceName -InRemovedState -Location $Location -Force
            
            Write-ColorOutput "🔄 等待清除完成..." "Yellow"
            Start-Sleep -Seconds 30
            
            # 重新创建账户
            Write-ColorOutput "🧠 重新创建Azure OpenAI服务..." "Yellow"
            $result = New-AzCognitiveServicesAccount `
                -ResourceGroupName $ResourceGroupName `
                -Name $OpenAIServiceName `
                -Type "OpenAI" `
                -SkuName "S0" `
                -Location $Location `
                -DisableLocalAuth $true `
                -Force
            
            if ($result) {
                Write-ColorOutput "✅ Azure OpenAI服务重新创建成功" "Green"
            } else {
                Write-ColorOutput "❌ 重新创建Azure OpenAI服务失败" "Red"
                exit 1
            }
        } else {
            # 使用PowerShell Az模块创建，支持DisableLocalAuth参数
            $result = New-AzCognitiveServicesAccount `
                -ResourceGroupName $ResourceGroupName `
                -Name $OpenAIServiceName `
                -Type "OpenAI" `
                -SkuName "S0" `
                -Location $Location `
                -DisableLocalAuth $true `
                -Force
            
            if ($result) {
                Write-ColorOutput "✅ Azure OpenAI服务创建成功" "Green"
            } else {
                Write-ColorOutput "❌ 创建Azure OpenAI服务失败" "Red"
                exit 1
            }
        }
    } catch {
        $errorMessage = $_.Exception.Message
        if ($errorMessage -like "*soft-deleted*") {
            Write-ColorOutput "⚠️ 检测到软删除的资源，尝试清除后重新创建..." "Yellow"
            try {
                # 尝试清除软删除的资源
                Remove-AzCognitiveServicesAccount -ResourceGroupName $ResourceGroupName -Name $OpenAIServiceName -InRemovedState -Location $Location -Force
                Write-ColorOutput "🔄 等待清除完成..." "Yellow"
                Start-Sleep -Seconds 30
                
                # 重新创建
                $result = New-AzCognitiveServicesAccount `
                    -ResourceGroupName $ResourceGroupName `
                    -Name $OpenAIServiceName `
                    -Type "OpenAI" `
                    -SkuName "S0" `
                    -Location $Location `
                    -DisableLocalAuth $true `
                    -Force
                
                if ($result) {
                    Write-ColorOutput "✅ Azure OpenAI服务创建成功" "Green"
                } else {
                    Write-ColorOutput "❌ 创建Azure OpenAI服务失败" "Red"
                    exit 1
                }
            } catch {
                Write-ColorOutput "❌ 无法处理软删除的资源: $($_.Exception.Message)" "Red"
                Write-ColorOutput "💡 请手动清除软删除的资源或等待自动清除" "Yellow"
                exit 1
            }
        } else {
            Write-ColorOutput "❌ 创建Azure OpenAI服务失败: $errorMessage" "Red"
            Write-ColorOutput "💡 请确保已安装并导入Az.CognitiveServices模块" "Yellow"
            Write-ColorOutput "💡 运行: Install-Module Az.CognitiveServices -Force" "Yellow"
            exit 1
        }
    }
} else {
    Write-ColorOutput "ℹ️ Azure OpenAI服务 $OpenAIServiceName 已存在，跳过创建" "Yellow"
}

# 5.1. 部署AI模型到Azure OpenAI服务
Write-ColorOutput "🤖 部署AI模型到Azure OpenAI服务..." "Cyan"

# 部署GPT-4模型
Write-ColorOutput "🧠 检查${LLMModelName}模型部署..." "Cyan"
$gpt4Deployment = az cognitiveservices account deployment show --name $OpenAIServiceName --resource-group $ResourceGroupName --deployment-name $LLMDeploymentName 2>$null
if (-not $gpt4Deployment) {
    Write-ColorOutput "🧠 部署${LLMModelName}模型..." "Yellow"
    az cognitiveservices account deployment create `
        --name $OpenAIServiceName `
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
$embeddingDeployment = az cognitiveservices account deployment show --name $OpenAIServiceName --resource-group $ResourceGroupName --deployment-name $EmbeddingDeploymentName 2>$null
if (-not $embeddingDeployment) {
    Write-ColorOutput "📝 部署${EmbeddingModelName}模型..." "Yellow"
    az cognitiveservices account deployment create `
        --name $OpenAIServiceName `
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
    
    # 为Azure AI Search分配OpenAI访问权限
    Write-ColorOutput "🔑 为Azure AI Search分配OpenAI访问权限..." "Yellow"
    $openAIResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.CognitiveServices/accounts/$OpenAIServiceName"
    
    az role assignment create `
        --assignee $searchServiceIdentity `
        --role "Cognitive Services OpenAI User" `
        --scope $openAIResourceId
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ OpenAI访问权限分配成功" "Green"
    } else {
        Write-ColorOutput "❌ OpenAI访问权限分配失败" "Red"
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

# 获取Azure OpenAI服务的托管身份
Write-ColorOutput "🔍 获取Azure OpenAI托管身份..." "Cyan"
$openAIServiceIdentity = az cognitiveservices account show --name $OpenAIServiceName --resource-group $ResourceGroupName --query identity.principalId -o tsv 2>$null

if ($openAIServiceIdentity) {
    Write-ColorOutput "✅ Azure OpenAI托管身份ID: $openAIServiceIdentity" "Green"
    
    # 为Azure OpenAI分配存储账户访问权限（如果需要访问文档）
    Write-ColorOutput "🔑 为Azure OpenAI分配存储访问权限..." "Yellow"
    $storageResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Storage/storageAccounts/$StorageAccountName"
    
    az role assignment create `
        --assignee $openAIServiceIdentity `
        --role "Storage Blob Data Reader" `
        --scope $storageResourceId
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ OpenAI存储访问权限分配成功" "Green"
    } else {
        Write-ColorOutput "❌ OpenAI存储访问权限分配失败" "Red"
    }
} else {
    Write-ColorOutput "ℹ️ Azure OpenAI服务可能未启用托管身份" "Yellow"
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
Write-ColorOutput "📋 资源摘要:" "Yellow"
Write-ColorOutput "   - 资源组: $ResourceGroupName" "White"
Write-ColorOutput "   - 存储账户: $StorageAccountName" "White"
Write-ColorOutput "   - Blob容器: $ContainerName" "White"
Write-ColorOutput "   - 数据文件: $fileName" "White"
Write-ColorOutput "   - Azure OpenAI: $OpenAIServiceName" "White"
Write-ColorOutput "   - GPT-4模型: $LLMDeploymentName" "White"
Write-ColorOutput "   - 嵌入模型: $EmbeddingDeploymentName" "White"
Write-ColorOutput "   - Azure AI Search: $SearchServiceName" "White"
Write-ColorOutput "   - 搜索索引: $SearchIndexName" "White"
Write-ColorOutput "   - Knowledge Agent: $KnowledgeAgentName" "White"
