# Azure Deployment Guide for Retail RAG Web App

## Quick Deployment Options

### Option 1: GitHub Actions (Recommended)

1. **Create Azure Resources:**
   ```bash
   # Login to Azure CLI
   az login
   
   # Create resource group
   az group create --name retail-rag-rg --location "East US"
   
   # Create App Service Plan
   az appservice plan create --name retail-rag-plan --resource-group retail-rag-rg --sku B1 --is-linux
   
   # Create Web App
   az webapp create --resource-group retail-rag-rg --plan retail-rag-plan --name retail-rag-web-app-[random] --runtime "DOTNETCORE|8.0"
   ```

2. **Get Publish Profile:**
   ```bash
   az webapp deployment list-publishing-profiles --name retail-rag-web-app-[random] --resource-group retail-rag-rg --xml
   ```

3. **Set up GitHub Secrets:**
   - Go to your GitHub repository → Settings → Secrets
   - Add `AZUREAPPSERVICE_PUBLISHPROFILE` with the XML content from step 2
   - Update `AZURE_WEBAPP_NAME` in `.github/workflows/azure-deploy.yml`

4. **Deploy:**
   - Push to main branch to trigger automatic deployment

### Option 2: Manual ZIP Deploy

1. **Build for Production:**
   ```bash
   dotnet publish -c Release -o ./publish
   ```

2. **Create ZIP:**
   - Compress the `./publish` folder contents

3. **Deploy:**
   - Go to: `https://[your-app-name].scm.azurewebsites.net/ZipDeploy`
   - Upload the ZIP file

### Option 3: Docker Container

1. **Build Docker Image:**
   ```bash
   docker build -t retail-rag-web-app .
   ```

2. **Deploy to Azure Container Instances:**
   ```bash
   az container create --resource-group retail-rag-rg --name retail-rag-container --image retail-rag-web-app --ports 80
   ```

## Environment Variables for Production

Set these in Azure App Service Configuration:

```
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com
AZURE_SEARCH_INDEX_NAME=your-index-name
AZURE_SEARCH_AGENT_NAME=retail-knowledge-agent
AZURE_OPENAI_GPT_DEPLOYMENT=gpt-4.1
ASPNETCORE_ENVIRONMENT=Production
```

## Post-Deployment Configuration

1. **Configure Managed Identity:**
   - Enable System-assigned managed identity in Azure App Service
   - Grant necessary permissions to Azure Search and OpenAI resources

2. **SSL/TLS:**
   - Azure App Service provides free SSL certificates
   - Custom domains can be configured if needed

3. **Monitoring:**
   - Enable Application Insights for monitoring
   - Set up log streaming for real-time debugging

## Performance Optimization

1. **App Service Plan:**
   - Use at least B1 (Basic) tier for production
   - Consider S1 (Standard) or higher for better performance

2. **Caching:**
   - Enable output caching for static content
   - Consider Redis cache for session state

3. **CDN:**
   - Use Azure CDN for static assets
   - Improves global performance

## Security Considerations

1. **Authentication:**
   - Configure Azure AD authentication if needed
   - Implement API key management

2. **Network Security:**
   - Configure IP restrictions if required
   - Use Application Gateway for advanced security

3. **Data Protection:**
   - Ensure HTTPS only
   - Configure proper CORS policies

## Troubleshooting

1. **Logs:**
   - Check Application Insights for errors
   - Use Log Stream for real-time debugging

2. **Common Issues:**
   - Environment variables not set
   - Managed identity permissions
   - Connection string configuration

## Cost Optimization

1. **App Service Plan:**
   - Use B1 for development/testing
   - Scale up for production traffic

2. **AI Services:**
   - Monitor token usage
   - Implement caching for repeated queries

3. **Storage:**
   - Use appropriate storage tiers
   - Clean up old logs and data

## Monitoring and Alerts

1. **Application Insights:**
   - Response times
   - Error rates
   - Dependency failures

2. **Azure Monitor:**
   - Resource utilization
   - Cost tracking
   - Performance metrics
