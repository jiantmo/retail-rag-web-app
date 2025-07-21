# Azure部署指南

## 前提条件

1. **Azure CLI** - [下载并安装](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
2. **Azure订阅** - 需要有效的Azure订阅
3. **Azure服务** - 需要以下Azure服务：
   - Azure OpenAI Service
   - Azure Cognitive Search
   - Azure App Service

## 快速部署

### 方法1: 使用快速部署脚本

```powershell
# 运行快速部署脚本
.\quick-deploy.ps1 -AppName "your-app-name"
```

### 方法2: 使用完整部署脚本

```powershell
# 自定义参数部署
.\deploy-to-azure.ps1 -ResourceGroupName "retail-rag-rg" -WebAppName "retail-rag-app" -Location "East Asia"
```

## 部署步骤详解

### 1. 登录Azure CLI

```bash
az login
```

### 2. 设置订阅（如果有多个订阅）

```bash
az account set --subscription "你的订阅ID"
```

### 3. 运行部署脚本

选择以下任一方式：

#### 选项A: 快速部署（推荐）
```powershell
.\quick-deploy.ps1 -AppName "retail-rag-demo"
```

#### 选项B: 自定义部署
```powershell
.\deploy-to-azure.ps1 -ResourceGroupName "my-rg" -WebAppName "my-app" -Location "East Asia" -Sku "B1"
```

### 4. 配置环境变量

部署完成后，在Azure门户中配置以下应用设置：

| 设置名称 | 描述 | 示例值 |
|---------|------|--------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI服务端点 | `https://your-openai.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API密钥 | `your-api-key` |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | GPT模型部署名称 | `gpt-4o-mini` |
| `AZURE_SEARCH_SERVICE_NAME` | Azure搜索服务名称 | `your-search-service` |
| `AZURE_SEARCH_API_KEY` | Azure搜索API密钥 | `your-search-key` |
| `AZURE_SEARCH_INDEX_NAME` | 搜索索引名称 | `retail-products` |

### 5. 配置步骤

1. 访问 [Azure门户](https://portal.azure.com)
2. 导航到你的Web App
3. 在左侧菜单选择 **配置** > **应用程序设置**
4. 点击 **+ 新建应用程序设置**
5. 添加上述所有环境变量
6. 点击 **保存**
7. 重启应用

## 手动部署（使用Visual Studio或CLI）

### 使用dotnet CLI

```bash
# 1. 构建项目
dotnet build --configuration Release

# 2. 发布项目
dotnet publish --configuration Release --output ./publish

# 3. 创建部署包
Compress-Archive -Path "./publish/*" -DestinationPath "./deploy.zip"

# 4. 部署到Azure
az webapp deploy --resource-group "your-rg" --name "your-app" --src-path "./deploy.zip" --type zip
```

### 使用Visual Studio

1. 右键点击项目 > **发布**
2. 选择 **Azure** > **Azure App Service (Windows)**
3. 登录Azure账户
4. 选择或创建App Service
5. 点击 **发布**

## 部署后验证

1. 访问应用URL: `https://your-app-name.azurewebsites.net`
2. 测试搜索功能
3. 检查日志: Azure门户 > App Service > 日志流

## 故障排除

### 常见问题

1. **应用启动失败**
   - 检查环境变量是否正确配置
   - 查看应用日志：Azure门户 > App Service > 日志流

2. **搜索功能不工作**
   - 验证Azure OpenAI和搜索服务的API密钥
   - 确认服务端点URL格式正确

3. **性能问题**
   - 考虑升级App Service计划（从F1升级到B1或更高）
   - 启用应用洞察（Application Insights）进行监控

### 日志查看

```bash
# 查看实时日志
az webapp log tail --name "your-app-name" --resource-group "your-rg"

# 下载日志
az webapp log download --name "your-app-name" --resource-group "your-rg"
```

## 成本优化

- **开发环境**: 使用F1（免费）计划
- **生产环境**: 使用B1或更高计划
- **自动缩放**: 配置基于负载的自动缩放

## 安全建议

1. 使用Azure Key Vault存储敏感配置
2. 启用HTTPS重定向
3. 配置自定义域名和SSL证书
4. 启用应用洞察监控

## 更新应用

重新运行部署脚本即可更新应用：

```powershell
.\quick-deploy.ps1 -AppName "your-app-name"
```

## 支持

如有问题，请检查：
- [Azure App Service文档](https://docs.microsoft.com/en-us/azure/app-service/)
- [Azure OpenAI文档](https://docs.microsoft.com/en-us/azure/cognitive-services/openai/)
- [Azure搜索文档](https://docs.microsoft.com/en-us/azure/search/)
