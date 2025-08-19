#!/bin/bash

# Quick Azure Deployment Script
# Run this in Azure Cloud Shell or with Azure CLI installed

# Configuration
RESOURCE_GROUP="retail-rag-rg"
LOCATION="East US"
APP_SERVICE_PLAN="retail-rag-plan"
WEB_APP_NAME="retail-rag-web-app-$(shuf -i 1000-9999 -n 1)"
SUBSCRIPTION_ID="your-subscription-id"  # Replace with your subscription ID

echo "🚀 Starting Azure deployment for Retail RAG Web App"
echo "Web App Name: $WEB_APP_NAME"

# Login check
echo "📋 Checking Azure login status..."
if ! az account show > /dev/null 2>&1; then
    echo "Please login to Azure first:"
    echo "az login"
    exit 1
fi

# Set subscription
echo "📋 Setting subscription..."
az account set --subscription "$SUBSCRIPTION_ID"

# Create resource group
echo "📦 Creating resource group: $RESOURCE_GROUP"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

# Create App Service Plan
echo "📦 Creating App Service Plan: $APP_SERVICE_PLAN"
az appservice plan create \
  --name "$APP_SERVICE_PLAN" \
  --resource-group "$RESOURCE_GROUP" \
  --sku B1 \
  --is-linux

# Create Web App
echo "📦 Creating Web App: $WEB_APP_NAME"
az webapp create \
  --resource-group "$RESOURCE_GROUP" \
  --plan "$APP_SERVICE_PLAN" \
  --name "$WEB_APP_NAME" \
  --runtime "DOTNETCORE:8.0"

# Configure app settings
echo "⚙️  Configuring app settings..."
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEB_APP_NAME" \
  --settings \
    ASPNETCORE_ENVIRONMENT=Production \
    WEBSITES_ENABLE_APP_SERVICE_STORAGE=false \
    WEBSITE_RUN_FROM_PACKAGE=1

# Enable system-assigned managed identity
echo "🔐 Enabling managed identity..."
az webapp identity assign \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEB_APP_NAME"

# Deploy application (if publish folder exists)
if [ -d "./publish" ]; then
    echo "📤 Deploying application..."
    cd publish
    zip -r ../app.zip .
    cd ..
    
    az webapp deployment source config-zip \
      --resource-group "$RESOURCE_GROUP" \
      --name "$WEB_APP_NAME" \
      --src app.zip
    
    echo "🎉 Application deployed successfully!"
else
    echo "⚠️  Publish folder not found. Run 'dotnet publish -c Release -o ./publish' first."
fi

# Get publish profile for GitHub Actions
echo "📋 Getting publish profile for GitHub Actions..."
az webapp deployment list-publishing-profiles \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEB_APP_NAME" \
  --xml > publish-profile.xml

echo ""
echo "✅ Deployment completed!"
echo "🌐 Web App URL: https://$WEB_APP_NAME.azurewebsites.net"
echo "📁 Publish profile saved to: publish-profile.xml"
echo ""
echo "📝 Next steps:"
echo "1. Configure environment variables in Azure Portal:"
echo "   - AZURE_SEARCH_ENDPOINT"
echo "   - AZURE_OPENAI_ENDPOINT"
echo "   - AZURE_SEARCH_INDEX_NAME"
echo "   - AZURE_SEARCH_AGENT_NAME"
echo "   - AZURE_OPENAI_GPT_DEPLOYMENT"
echo ""
echo "2. Grant managed identity permissions to:"
echo "   - Azure Search Service (Search Service Contributor)"
echo "   - Azure OpenAI Service (Cognitive Services User)"
echo ""
echo "3. For GitHub Actions deployment:"
echo "   - Copy publish-profile.xml content to GitHub Secrets as 'AZUREAPPSERVICE_PUBLISHPROFILE'"
echo "   - Update AZURE_WEBAPP_NAME in .github/workflows/azure-deploy.yml to: $WEB_APP_NAME"
