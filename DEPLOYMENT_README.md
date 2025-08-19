# 🚀 Azure Deployment Guide

## Prerequisites

- Azure subscription
- Azure CLI installed or Azure Cloud Shell access
- .NET 8 SDK (for local development)

## Quick Start

### Option 1: Automated PowerShell Script (Windows)

```powershell
# 1. Update subscription ID in azure-deploy.ps1
# 2. Run the deployment script
.\azure-deploy.ps1
```

### Option 2: Automated Bash Script (Linux/macOS)

```bash
# 1. Update subscription ID in deploy-to-azure.sh
# 2. Make script executable and run
chmod +x deploy-to-azure.sh
./deploy-to-azure.sh
```

### Option 3: Manual Azure CLI Commands

```bash
# Login to Azure
az login

# Set variables
RESOURCE_GROUP="retail-rag-rg"
LOCATION="East US"
APP_SERVICE_PLAN="retail-rag-plan"
WEB_APP_NAME="retail-rag-web-app-$(shuf -i 1000-9999 -n 1)"

# Create resources
az group create --name $RESOURCE_GROUP --location $LOCATION
az appservice plan create --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP --sku B1 --is-linux
az webapp create --resource-group $RESOURCE_GROUP --plan $APP_SERVICE_PLAN --name $WEB_APP_NAME --runtime "DOTNETCORE:8.0"

# Deploy application
dotnet publish -c Release -o ./publish
cd publish && zip -r ../app.zip . && cd ..
az webapp deployment source config-zip --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --src app.zip
```

## Post-Deployment Configuration

### 1. Environment Variables

Configure these in Azure Portal → App Service → Configuration:

```
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com
AZURE_SEARCH_INDEX_NAME=your-index-name
AZURE_SEARCH_AGENT_NAME=retail-knowledge-agent
AZURE_OPENAI_GPT_DEPLOYMENT=gpt-4.1
ASPNETCORE_ENVIRONMENT=Production
```

### 2. Managed Identity Permissions

Grant the App Service managed identity these roles:

**Azure Search Service:**
- Search Service Contributor
- Search Index Data Contributor
- Search Index Data Reader

**Azure OpenAI Service:**
- Cognitive Services User

```bash
# Get the managed identity principal ID
PRINCIPAL_ID=$(az webapp identity show --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --query principalId --output tsv)

# Grant Search permissions
az role assignment create --assignee $PRINCIPAL_ID --role "Search Service Contributor" --scope /subscriptions/{subscription-id}/resourceGroups/{search-rg}/providers/Microsoft.Search/searchServices/{search-service}

# Grant OpenAI permissions
az role assignment create --assignee $PRINCIPAL_ID --role "Cognitive Services User" --scope /subscriptions/{subscription-id}/resourceGroups/{openai-rg}/providers/Microsoft.CognitiveServices/accounts/{openai-service}
```

## GitHub Actions Setup (CI/CD)

### 1. Get Publish Profile

```bash
az webapp deployment list-publishing-profiles --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --xml
```

### 2. Configure GitHub Secrets

Go to GitHub Repository → Settings → Secrets and variables → Actions:

- `AZUREAPPSERVICE_PUBLISHPROFILE`: Paste the XML from step 1

### 3. Update Workflow

Edit `.github/workflows/azure-deploy.yml`:

```yaml
env:
  AZURE_WEBAPP_NAME: your-actual-app-name    # Update this
```

### 4. Deploy

Push to main branch to trigger automatic deployment.

## Docker Deployment (Alternative)

### Build and Push to Azure Container Registry

```bash
# Create ACR
az acr create --resource-group $RESOURCE_GROUP --name retailragacr --sku Basic

# Build and push
az acr build --registry retailragacr --image retail-rag-web-app:latest .

# Create container app
az containerapp create \
  --name retail-rag-container-app \
  --resource-group $RESOURCE_GROUP \
  --image retailragacr.azurecr.io/retail-rag-web-app:latest \
  --environment retail-rag-env \
  --ingress external \
  --target-port 80
```

## Monitoring and Troubleshooting

### Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app retail-rag-insights \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --application-type web

# Get instrumentation key
az monitor app-insights component show \
  --app retail-rag-insights \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey
```

Add to app settings:
```
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey={key};IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com/;LiveEndpoint=https://eastus.livediagnostics.monitor.azure.com/
```

### Log Streaming

```bash
# View live logs
az webapp log tail --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME

# Download logs
az webapp log download --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME
```

### Common Issues

1. **Authentication Errors:**
   - Verify managed identity is enabled
   - Check role assignments
   - Confirm environment variables are set

2. **Performance Issues:**
   - Upgrade to higher App Service Plan tier
   - Enable Application Insights for monitoring
   - Consider implementing caching

3. **Deployment Failures:**
   - Check deployment logs in Azure Portal
   - Verify .NET 8 runtime is available
   - Ensure web.config is properly configured

## Security Configuration

### HTTPS Only

```bash
az webapp update --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --https-only true
```

### Custom Domain and SSL

```bash
# Add custom domain
az webapp config hostname add --webapp-name $WEB_APP_NAME --resource-group $RESOURCE_GROUP --hostname yourdomain.com

# Enable SSL
az webapp config ssl bind --certificate-thumbprint {thumbprint} --ssl-type SNI --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME
```

## Cost Optimization

### App Service Plan Tiers

- **B1 (Basic)**: $13.14/month - Good for development/testing
- **S1 (Standard)**: $73.00/month - Production ready with staging slots
- **P1v2 (Premium)**: $85.00/month - High performance with auto-scaling

### Scaling

```bash
# Manual scaling
az appservice plan update --number-of-workers 2 --resource-group $RESOURCE_GROUP --name $APP_SERVICE_PLAN

# Auto-scaling rules
az monitor autoscale create \
  --resource-group $RESOURCE_GROUP \
  --resource $WEB_APP_NAME \
  --resource-type Microsoft.Web/serverfarms \
  --name retail-rag-autoscale \
  --min-count 1 \
  --max-count 5 \
  --count 1
```

## Backup and Disaster Recovery

### Automated Backups

```bash
az webapp config backup create \
  --resource-group $RESOURCE_GROUP \
  --webapp-name $WEB_APP_NAME \
  --backup-name initial-backup \
  --storage-account-url "https://yourstorageaccount.blob.core.windows.net/backups?{sas-token}"
```

### Deployment Slots

```bash
# Create staging slot
az webapp deployment slot create --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --slot staging

# Deploy to staging
az webapp deployment source config-zip --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --slot staging --src app.zip

# Swap staging to production
az webapp deployment slot swap --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --slot staging --target-slot production
```

---

## Support

For issues and questions:
1. Check Application Insights for errors
2. Review deployment logs in Azure Portal
3. Use Log Stream for real-time debugging
4. Consult Azure documentation for App Service troubleshooting
