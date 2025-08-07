# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a retail RAG (Retrieval Augmented Generation) web application built with ASP.NET Core 8.0 that provides intelligent product search and recommendations using Azure AI services. The application combines Azure AI Search, Azure OpenAI, and conversational UI to deliver natural language product queries.

## Architecture

The application follows a standard ASP.NET Core MVC pattern with the following key components:

### Core Services
- **AgenticSearchService**: Orchestrates complex multi-step searches using knowledge agents
- **AgenticRetrievalService**: Handles retrieval operations with Azure AI Search
- **KnowledgeAgentManagementService**: Manages Azure AI Search knowledge agents
- **DataverseService**: Integration with Microsoft Dataverse for product data
- **RagService**: Core RAG functionality for search and generation

### Controllers
- **AgenticController** (`/agentic`): Handles agentic search operations with both regular and streaming endpoints
- **KnowledgeAgentController**: Manages knowledge agent operations
- **HomeController**: Main application interface
- **SearchController**: Traditional search functionality

### Key Models
- **AgenticSearchResponse**: Response structure for agentic search operations
- **ProductResult**: Product search result model
- **DataverseSearchRequest**: Request model for Dataverse operations

## Development Commands

### Build and Run
```bash
# Restore dependencies
dotnet restore

# Build the project
dotnet build

# Run in development mode
dotnet run

# Run with specific profile
dotnet run --launch-profile https
```

### Development Environment
The application runs on:
- HTTPS: `https://localhost:5001` 
- HTTP: `http://localhost:5000`

### Configuration
- Uses `.env` file for environment variables (loaded via dotenv.net)
- Configuration tokens in `appsettings.json` use `#{TOKEN_NAME}#` format
- User secrets configured with ID: `e392b6bb-ba16-4a5f-b831-be3d24e15888`

## Azure Integration

### Required Azure Services
- **Azure OpenAI Service**: For GPT models and embeddings
- **Azure AI Search**: For semantic search and knowledge agents
- **Azure Identity**: Uses DefaultAzureCredential for authentication

### Key Dependencies
- `Azure.AI.OpenAI` (2.1.0): OpenAI service integration
- `Azure.Search.Documents` (11.7.0-beta.4): Search service integration
- `Azure.Identity` (1.12.0): Azure authentication
- `dotenv.net` (3.1.3): Environment variable management

## Deployment

### PowerShell Scripts Available
- `deploy-to-azure.ps1`: Full Azure deployment
- `verify-permissions.ps1`: Check Azure permissions
- `fix-indexer.ps1`: Fix search indexer issues
- `test_api.ps1`: API testing script
- `acs-agentic-search-resource-provision-jiantmo-mos.ps1`: Azure Cognitive Search provisioning

### Deployment Options
1. **Self-hosted**: `dotnet publish -c Release`
2. **Azure App Service**: Use provided deployment scripts
3. **Container**: Application is containerization-ready

## API Endpoints

### Agentic Search
- `POST /agentic/search`: Standard agentic search
- `POST /agentic/stream`: Streaming agentic search

### Knowledge Agent Management
- Various endpoints for managing Azure AI Search knowledge agents

## Development Notes

- Target Framework: .NET 8.0
- Uses nullable reference types enabled
- Implicit usings enabled
- JSON serialization configured for case-insensitive property matching
- HttpClient services registered for external API calls
- HSTS enabled for production environments only

## Environment Variables

The application expects these environment variables (typically in `.env` file):
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_OPENAI_ENDPOINT` 
- `AZURE_SEARCH_INDEX_NAME`
- Additional Azure service configuration as needed

## Testing

Use the provided `test_api.ps1` PowerShell script for API testing. The application includes test data files:
- `AdventureWorksDemoDataProducts_with_embedding.csv/json`
- `TestCase1.json`
- `sample_data.json`