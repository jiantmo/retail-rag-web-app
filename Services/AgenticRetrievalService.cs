using Azure;
using Azure.Core;
using Azure.Identity;
using Azure.Search.Documents;
using Azure.Search.Documents.Models;
using System.Text.Json;
using dotenv.net;

namespace retail_rag_web_app.Services
{
    public class AgenticRetrievalService
    {
        private readonly HttpClient _httpClient;
        private readonly string _searchEndpoint;
        private readonly string _agentName;
        private readonly string _indexName;
        private readonly string _openAIEndpoint;
        private readonly string _openAIDeployment;
        private readonly TokenCredential _credential;
        private readonly ILogger<AgenticRetrievalService> _logger;

        public AgenticRetrievalService(HttpClient httpClient, IConfiguration configuration, ILogger<AgenticRetrievalService> logger)
        {
            _httpClient = httpClient;
            _logger = logger;

            // Load environment variables
            DotEnv.Load();

            _searchEndpoint = Environment.GetEnvironmentVariable("AZURE_SEARCH_ENDPOINT") 
                ?? configuration["AZURE_SEARCH_ENDPOINT"] 
                ?? throw new ArgumentException("AZURE_SEARCH_ENDPOINT not configured");

            _agentName = Environment.GetEnvironmentVariable("AZURE_SEARCH_AGENT_NAME") 
                ?? configuration["AzureSearch:AgentName"] 
                ?? "retail-knowledge-agent";

            _indexName = Environment.GetEnvironmentVariable("AZURE_SEARCH_INDEX_NAME") 
                ?? configuration["AZURE_SEARCH_INDEX_NAME"] 
                ?? "rag-retail";

            _openAIEndpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") 
                ?? configuration["AZURE_OPENAI_ENDPOINT"] 
                ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT not configured");

            _openAIDeployment = Environment.GetEnvironmentVariable("AZURE_OPENAI_GPT_DEPLOYMENT") 
                ?? configuration["AZURE_OPENAI_GPT_DEPLOYMENT"] 
                ?? "gpt-4o-mini";

            // Use Managed Identity or DefaultAzureCredential for authentication
            var managedIdentityClientId = Environment.GetEnvironmentVariable("AZURE_CLIENT_ID") 
                ?? configuration["AzureManagedIdentity:ClientId"];
            if (!string.IsNullOrEmpty(managedIdentityClientId))
            {
                _credential = new ManagedIdentityCredential(managedIdentityClientId);
                _logger.LogInformation("Using ManagedIdentityCredential with ClientId: {ClientId}", managedIdentityClientId);
            }
            else
            {
                _credential = new DefaultAzureCredential();
                _logger.LogInformation("Using DefaultAzureCredential");
            }
        }

        public async Task<string> CreateKnowledgeAgentAsync()
        {
            try
            {
                var agentDefinition = new
                {
                    name = _agentName,
                    targetIndexes = new[]
                    {
                        new
                        {
                            indexName = _indexName,
                            defaultRerankerThreshold = 2.5,
                            defaultIncludeReferenceSourceData = true,
                            defaultMaxDocsForReranker = 200
                        }
                    },
                    models = new[]
                    {
                        new
                        {
                            kind = "azureOpenAI",
                            azureOpenAIParameters = new
                            {
                                resourceUri = _openAIEndpoint,
                                apiKey = (string?)null,  // Use null for Azure AD authentication
                                deploymentId = _openAIDeployment,
                                modelName = "gpt-4o-mini"
                            }
                        }
                    },
                    requestLimits = new
                    {
                        maxOutputSize = 5000,
                        maxRuntimeInSeconds = 60
                    },
                    encryptionKey = new { }
                };

                var json = JsonSerializer.Serialize(agentDefinition, new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.CamelCase
                });

                var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");
                var url = $"{_searchEndpoint}/agents/{_agentName}?api-version=2025-05-01-preview";

                // Get Bearer token for authentication
                var tokenResult = await _credential.GetTokenAsync(new TokenRequestContext(new[] { "https://search.azure.com/.default" }), CancellationToken.None);
                _httpClient.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", tokenResult.Token);

                _logger.LogInformation("Creating knowledge agent at: {Url}", url);
                
                var response = await _httpClient.PutAsync(url, content);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseContent = await response.Content.ReadAsStringAsync();
                    _logger.LogInformation("Knowledge agent created successfully");
                    return responseContent;
                }
                else
                {
                    var errorContent = await response.Content.ReadAsStringAsync();
                    _logger.LogError("Failed to create knowledge agent. Status: {Status}, Error: {Error}", 
                        response.StatusCode, errorContent);
                    throw new HttpRequestException($"Failed to create knowledge agent: {response.StatusCode} - {errorContent}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error creating knowledge agent");
                throw;
            }
        }

        public async Task<string> CheckKnowledgeAgentAsync()
        {
            try
            {
                var url = $"{_searchEndpoint}/agents/{_agentName}?api-version=2025-05-01-preview";
                
                // Get Bearer token for authentication
                var tokenResult = await _credential.GetTokenAsync(new TokenRequestContext(new[] { "https://search.azure.com/.default" }), CancellationToken.None);
                _httpClient.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", tokenResult.Token);
                
                var response = await _httpClient.GetAsync(url);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseContent = await response.Content.ReadAsStringAsync();
                    _logger.LogInformation("Knowledge agent found");
                    return responseContent;
                }
                else if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
                {
                    _logger.LogInformation("Knowledge agent not found, creating new one");
                    return await CreateKnowledgeAgentAsync();
                }
                else
                {
                    var errorContent = await response.Content.ReadAsStringAsync();
                    _logger.LogError("Failed to check knowledge agent. Status: {Status}, Error: {Error}", 
                        response.StatusCode, errorContent);
                    throw new HttpRequestException($"Failed to check knowledge agent: {response.StatusCode} - {errorContent}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error checking knowledge agent");
                throw;
            }
        }

        public async Task<string> AgenticRetrieveAsync(string userQuery, string? systemPrompt = null)
        {
            try
            {
                // Ensure knowledge agent exists
                await CheckKnowledgeAgentAsync();

                var retrieveRequest = new
                {
                    messages = new[]
                    {
                        new
                        {
                            role = "user",
                            content = new[]
                            {
                                new
                                {
                                    type = "text",
                                    text = (systemPrompt ?? @"I am a professional retail product consultant with comprehensive access to our product database. My role is to provide personalized product recommendations based on customer needs, preferences, and budget constraints.

My approach includes:
1. Understanding specific customer needs and requirements
2. Recommending 2-3 most suitable products with clear rationale
3. Providing detailed product information including pricing and value analysis
4. Asking clarifying questions when needed
5. Suggesting alternatives when exact matches aren't available
6. For price-related queries, I carefully filter products within the specified budget range

I specialize in handling price range queries such as 'under $50', 'below $100', 'between $20-$100', 'less than $50', etc. I understand various price expressions and will find products that match the budget criteria.

I'm here to help you make informed purchasing decisions.") + "\n\nUser query: " + userQuery
                                }
                            }
                        }
                    },
                    targetIndexParams = new[]
                    {
                        new
                        {
                            indexName = _indexName,
                            includeReferenceSourceData = true,
                            rerankerThreshold = 1.5,  // 降低阈值以包含更多可能相关的结果
                            maxDocsForReranker = 300   // 增加候选文档数以提高复杂查询的召回率
                        }
                    }
                };

                var json = JsonSerializer.Serialize(retrieveRequest, new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.CamelCase
                });

                var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");
                var url = $"{_searchEndpoint}/agents/{_agentName}/retrieve?api-version=2025-05-01-preview";

                // Get Bearer token for authentication
                var tokenResult = await _credential.GetTokenAsync(new TokenRequestContext(new[] { "https://search.azure.com/.default" }), CancellationToken.None);
                _httpClient.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", tokenResult.Token);

                _logger.LogInformation("Performing agentic retrieval for query: {Query}", userQuery);
                
                var response = await _httpClient.PostAsync(url, content);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseContent = await response.Content.ReadAsStringAsync();
                    _logger.LogInformation("Agentic retrieval completed successfully");
                    
                    // Return the full response content to allow proper parsing in the frontend
                    return responseContent;
                }
                else
                {
                    var errorContent = await response.Content.ReadAsStringAsync();
                    _logger.LogError("Agentic retrieval failed. Status: {Status}, Error: {Error}", 
                        response.StatusCode, errorContent);
                    throw new HttpRequestException($"Agentic retrieval failed: {response.StatusCode} - {errorContent}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in agentic retrieval");
                throw;
            }
        }

        public async IAsyncEnumerable<string> AgenticRetrieveStreamAsync(string userQuery, string? systemPrompt = null)
        {
            // For now, we'll simulate streaming by chunking the response
            // In future versions, Azure AI Search may support streaming agentic retrieval
            var response = await AgenticRetrieveAsync(userQuery, systemPrompt);
            
            // Split the response into chunks for a streaming-like experience
            var words = response.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            var chunkSize = 3; // Number of words per chunk
            
            for (int i = 0; i < words.Length; i += chunkSize)
            {
                var chunk = string.Join(" ", words.Skip(i).Take(chunkSize));
                if (i + chunkSize < words.Length)
                {
                    chunk += " ";
                }
                
                yield return chunk;
                
                // Add a small delay to simulate streaming
                await Task.Delay(50);
            }
        }
    }
}
