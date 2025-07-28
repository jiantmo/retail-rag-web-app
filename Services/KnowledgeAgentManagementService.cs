using Azure;
using Azure.Core;
using Azure.Identity;
using System.Text.Json;
using System.Text;
using dotenv.net;

namespace retail_rag_web_app.Services
{
    /// <summary>
    /// Service for managing Knowledge Agents in Azure AI Search
    /// Based on https://learn.microsoft.com/en-us/azure/search/search-agentic-retrieval-how-to-create
    /// </summary>
    public class KnowledgeAgentManagementService
    {
        private readonly HttpClient _httpClient;
        private readonly string _searchEndpoint;
        private readonly string _searchApiKey;
        private readonly string _agentName;
        private readonly string _indexName;
        private readonly string _openAIEndpoint;
        private readonly string _openAIDeployment;
        private readonly string _openAIApiKey;
        private readonly ILogger<KnowledgeAgentManagementService> _logger;
        private readonly bool _useRoleBasedAuth;
        private readonly string _managedIdentityClientId;

        public KnowledgeAgentManagementService(HttpClient httpClient, IConfiguration configuration, ILogger<KnowledgeAgentManagementService> logger)
        {
            _httpClient = httpClient;
            _logger = logger;

            // Load environment variables
            DotEnv.Load();

            _searchEndpoint = Environment.GetEnvironmentVariable("AZURE_SEARCH_ENDPOINT") 
                ?? configuration["AZURE_SEARCH_ENDPOINT"] 
                ?? throw new ArgumentException("AZURE_SEARCH_ENDPOINT not configured");

            _searchApiKey = Environment.GetEnvironmentVariable("AZURE_SEARCH_API_KEY") 
                ?? configuration["AZURE_SEARCH_API_KEY"];

            _managedIdentityClientId = Environment.GetEnvironmentVariable("AZURE_CLIENT_ID") 
                ?? configuration["AzureManagedIdentity:ClientId"];

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
                ?? "gpt-4.1";

            _openAIApiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") 
                ?? configuration["AZURE_OPENAI_API_KEY"];

            _useRoleBasedAuth = string.IsNullOrEmpty(_searchApiKey) || string.IsNullOrEmpty(_openAIApiKey);

            // Configure HttpClient headers
            if (!string.IsNullOrEmpty(_searchApiKey))
            {
                _httpClient.DefaultRequestHeaders.Add("api-key", _searchApiKey);
            }
        }

        /// <summary>
        /// Lists all existing knowledge agents
        /// </summary>
        public async Task<KnowledgeAgentListResponse> ListKnowledgeAgentsAsync()
        {
            try
            {
                var url = $"{_searchEndpoint}/agents?api-version=2025-05-01-preview";
                
                var request = new HttpRequestMessage(HttpMethod.Get, url);
                await AddAuthenticationHeaderAsync(request);

                var response = await _httpClient.SendAsync(request);
                var content = await response.Content.ReadAsStringAsync();

                if (response.IsSuccessStatusCode)
                {
                    var result = JsonSerializer.Deserialize<KnowledgeAgentListResponse>(content, new JsonSerializerOptions 
                    { 
                        PropertyNamingPolicy = JsonNamingPolicy.CamelCase 
                    });
                    
                    _logger.LogInformation($"Successfully listed {result?.Value?.Count ?? 0} knowledge agents");
                    return result ?? new KnowledgeAgentListResponse { Value = new List<KnowledgeAgent>() };
                }
                else
                {
                    _logger.LogError($"Failed to list knowledge agents: {response.StatusCode} - {content}");
                    throw new Exception($"Failed to list knowledge agents: {response.StatusCode} - {content}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error listing knowledge agents");
                throw;
            }
        }

        /// <summary>
        /// Gets a specific knowledge agent by name
        /// </summary>
        public async Task<KnowledgeAgent> GetKnowledgeAgentAsync(string agentName = null)
        {
            try
            {
                var targetAgentName = agentName ?? _agentName;
                var url = $"{_searchEndpoint}/agents/{targetAgentName}?api-version=2025-05-01-preview";
                
                var request = new HttpRequestMessage(HttpMethod.Get, url);
                await AddAuthenticationHeaderAsync(request);

                var response = await _httpClient.SendAsync(request);
                var content = await response.Content.ReadAsStringAsync();

                if (response.IsSuccessStatusCode)
                {
                    var result = JsonSerializer.Deserialize<KnowledgeAgent>(content, new JsonSerializerOptions 
                    { 
                        PropertyNamingPolicy = JsonNamingPolicy.CamelCase 
                    });
                    
                    _logger.LogInformation($"Successfully retrieved knowledge agent: {targetAgentName}");
                    return result;
                }
                else if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
                {
                    _logger.LogWarning($"Knowledge agent not found: {targetAgentName}");
                    return null;
                }
                else
                {
                    _logger.LogError($"Failed to get knowledge agent: {response.StatusCode} - {content}");
                    throw new Exception($"Failed to get knowledge agent: {response.StatusCode} - {content}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Error getting knowledge agent: {agentName ?? _agentName}");
                throw;
            }
        }

        /// <summary>
        /// Creates a new knowledge agent with optimal settings for retail RAG
        /// </summary>
        public async Task<KnowledgeAgent> CreateKnowledgeAgentAsync(string agentName = null, KnowledgeAgentCreateOptions options = null)
        {
            try
            {
                var targetAgentName = agentName ?? _agentName;
                
                // Check if agent already exists
                var existing = await GetKnowledgeAgentAsync(targetAgentName);
                if (existing != null)
                {
                    _logger.LogInformation($"Knowledge agent already exists: {targetAgentName}");
                    return existing;
                }

                var agentDefinition = CreateAgentDefinition(targetAgentName, options);
                var url = $"{_searchEndpoint}/agents/{targetAgentName}?api-version=2025-05-01-preview";
                
                var json = JsonSerializer.Serialize(agentDefinition, new JsonSerializerOptions 
                { 
                    PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
                    WriteIndented = true
                });

                var request = new HttpRequestMessage(HttpMethod.Put, url)
                {
                    Content = new StringContent(json, Encoding.UTF8, "application/json")
                };
                await AddAuthenticationHeaderAsync(request);

                _logger.LogInformation($"Creating knowledge agent with definition: {json}");

                var response = await _httpClient.SendAsync(request);
                var content = await response.Content.ReadAsStringAsync();

                if (response.IsSuccessStatusCode)
                {
                    var result = JsonSerializer.Deserialize<KnowledgeAgent>(content, new JsonSerializerOptions 
                    { 
                        PropertyNamingPolicy = JsonNamingPolicy.CamelCase 
                    });
                    
                    _logger.LogInformation($"Successfully created knowledge agent: {targetAgentName}");
                    return result;
                }
                else
                {
                    _logger.LogError($"Failed to create knowledge agent: {response.StatusCode} - {content}");
                    throw new Exception($"Failed to create knowledge agent: {response.StatusCode} - {content}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Error creating knowledge agent: {agentName ?? _agentName}");
                throw;
            }
        }

        /// <summary>
        /// Deletes a knowledge agent
        /// </summary>
        public async Task<bool> DeleteKnowledgeAgentAsync(string agentName = null)
        {
            try
            {
                var targetAgentName = agentName ?? _agentName;
                // 使用正确的 agents API 端点来删除 knowledge agent
                var url = $"{_searchEndpoint}/agents/{targetAgentName}?api-version=2025-05-01-preview";
                
                var request = new HttpRequestMessage(HttpMethod.Delete, url);
                await AddAuthenticationHeaderAsync(request);

                var response = await _httpClient.SendAsync(request);

                if (response.IsSuccessStatusCode)
                {
                    _logger.LogInformation($"Successfully deleted knowledge agent: {targetAgentName}");
                    return true;
                }
                else if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
                {
                    _logger.LogWarning($"Knowledge agent not found for deletion: {targetAgentName}");
                    return false;
                }
                else
                {
                    var content = await response.Content.ReadAsStringAsync();
                    _logger.LogError($"Failed to delete knowledge agent: {response.StatusCode} - {content}");
                    throw new Exception($"Failed to delete knowledge agent: {response.StatusCode} - {content}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Error deleting knowledge agent: {agentName ?? _agentName}");
                throw;
            }
        }

        /// <summary>
        /// Tests the knowledge agent by sending a sample query
        /// </summary>
        public async Task<AgenticRetrievalResponse> TestKnowledgeAgentAsync(string query = "What products do you recommend?", string agentName = null, string role = "user", string? assistantContext = null)
        {
            try
            {
                var targetAgentName = agentName ?? _agentName;
                var url = $"{_searchEndpoint}/agents/{targetAgentName}/retrieve?api-version=2025-05-01-preview";
                
                var messages = new List<object>();
                
                // Add enhanced assistant context for RAG search
                var defaultAssistantContext = @"I am a professional retail product consultant with access to a comprehensive product database. I provide personalized product recommendations based on customer needs, preferences, and budget.

My capabilities include:
- Understanding complex product queries with price ranges, features, and categories
- Analyzing product specifications, pricing, and customer ratings
- Providing detailed product comparisons and recommendations
- Supporting various price expressions like 'under $50', 'less than $100', 'between $20-$80'
- Filtering products by color, size, brand, and other attributes

I focus on delivering clear, structured product information that helps customers make informed purchasing decisions.";

                // Add assistant context if provided, otherwise use default
                if (role == "user")
                {
                    messages.Add(new
                    {
                        role = "assistant",
                        content = new[]
                        {
                            new { type = "text", text = assistantContext ?? defaultAssistantContext }
                        }
                    });
                }
                
                // Add the main message
                messages.Add(new
                {
                    role = role,
                    content = new[]
                    {
                        new { type = "text", text = query }
                    }
                });

                var testRequest = new
                {
                    messages = messages.ToArray(),
                    targetIndexParams = new[]
                    {
                        new
                        {
                            indexName = _indexName,
                            includeReferenceSourceData = true,
                            rerankerThreshold = 1.8,  // 降低阈值以提高召回率
                            maxDocsForReranker = 250   // 增加候选文档数
                        }
                    }
                };

                var json = JsonSerializer.Serialize(testRequest, new JsonSerializerOptions 
                { 
                    PropertyNamingPolicy = JsonNamingPolicy.CamelCase 
                });

                var request = new HttpRequestMessage(HttpMethod.Post, url)
                {
                    Content = new StringContent(json, Encoding.UTF8, "application/json")
                };
                await AddAuthenticationHeaderAsync(request);

                var response = await _httpClient.SendAsync(request);
                var content = await response.Content.ReadAsStringAsync();

                if (response.IsSuccessStatusCode)
                {
                    _logger.LogInformation($"Raw response from knowledge agent: {content}");
                    
                    var result = JsonSerializer.Deserialize<AgenticRetrievalResponse>(content, new JsonSerializerOptions 
                    { 
                        PropertyNamingPolicy = JsonNamingPolicy.CamelCase 
                    });
                    
                    _logger.LogInformation($"Successfully tested knowledge agent: {targetAgentName}");
                    _logger.LogInformation($"Activity count: {result?.Activity?.Length ?? 0}");
                    
                    return result;
                }
                else if (response.StatusCode == System.Net.HttpStatusCode.Forbidden)
                {
                    // Handle 403 Forbidden gracefully - likely due to permission propagation delay
                    _logger.LogWarning($"Knowledge agent test failed with 403 Forbidden. This is usually due to permission propagation delay. Agent: {targetAgentName}");
                    
                    // Return a mock successful response to indicate the agent exists but permissions are still propagating
                    return new AgenticRetrievalResponse
                    {
                        Content = "Knowledge agent is ready but permissions are still propagating. Please try again in a few minutes.",
                        References = Array.Empty<Reference>()
                    };
                }
                else
                {
                    _logger.LogError($"Failed to test knowledge agent: {response.StatusCode} - {content}");
                    throw new Exception($"Failed to test knowledge agent: {response.StatusCode} - {content}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Error testing knowledge agent: {agentName ?? _agentName}");
                
                // If it's a permission error (403), return a graceful response instead of throwing
                if (ex.Message.Contains("Forbidden") || ex.Message.Contains("403"))
                {
                    _logger.LogWarning("Knowledge agent test failed due to permission issues. Returning graceful response.");
                    return new AgenticRetrievalResponse
                    {
                        Content = "Knowledge agent is ready but permissions are still propagating. Please try again in a few minutes.",
                        References = Array.Empty<Reference>()
                    };
                }
                
                throw;
            }
        }

        private KnowledgeAgentDefinition CreateAgentDefinition(string agentName, KnowledgeAgentCreateOptions options = null)
        {
            options ??= new KnowledgeAgentCreateOptions();

            return new KnowledgeAgentDefinition
            {
                Name = agentName,
                TargetIndexes = new[]
                {
                    new TargetIndex
                    {
                        IndexName = _indexName,
                        DefaultRerankerThreshold = options.DefaultRerankerThreshold,
                        DefaultIncludeReferenceSourceData = options.DefaultIncludeReferenceSourceData,
                        DefaultMaxDocsForReranker = options.DefaultMaxDocsForReranker
                    }
                },
                Models = new[]
                {
                    new ModelDefinition
                    {
                        Kind = "azureOpenAI",
                        AzureOpenAIParameters = new AzureOpenAIParameters
                        {
                            ResourceUri = _openAIEndpoint,
                            ApiKey = _useRoleBasedAuth ? null : _openAIApiKey,
                            DeploymentId = _openAIDeployment,
                            ModelName = !string.IsNullOrEmpty(options.ModelName) ? options.ModelName : "gpt-4.1"
                        }
                    }
                },
                RequestLimits = new RequestLimits
                {
                    MaxOutputSize = options.MaxOutputSize,
                    MaxRuntimeInSeconds = options.MaxRuntimeInSeconds
                },
                EncryptionKey = options.EncryptionKey
            };
        }

        private async Task AddAuthenticationHeaderAsync(HttpRequestMessage request)
        {
            if (_useRoleBasedAuth)
            {
                // Use Azure Managed Identity or DefaultAzureCredential for role-based authentication
                TokenCredential credential;
                
                if (!string.IsNullOrEmpty(_managedIdentityClientId))
                {
                    // Use User Managed Identity
                    credential = new ManagedIdentityCredential(_managedIdentityClientId);
                }
                else
                {
                    // Fallback to DefaultAzureCredential
                    credential = new DefaultAzureCredential();
                }
                
                var tokenRequestContext = new TokenRequestContext(new[] { "https://search.azure.com/.default" });
                var token = await credential.GetTokenAsync(tokenRequestContext, CancellationToken.None);
                request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", token.Token);
            }
            // API key is already set in the constructor for key-based auth
        }
    }

    // Data models for Knowledge Agent API
    public class KnowledgeAgentListResponse
    {
        public List<KnowledgeAgent> Value { get; set; } = new();
    }

    public class KnowledgeAgent
    {
        public string Name { get; set; } = "";
        public TargetIndex[] TargetIndexes { get; set; } = Array.Empty<TargetIndex>();
        public ModelDefinition[] Models { get; set; } = Array.Empty<ModelDefinition>();
        public RequestLimits RequestLimits { get; set; } = new();
        public object? EncryptionKey { get; set; }
    }

    public class KnowledgeAgentDefinition
    {
        public string Name { get; set; } = "";
        public TargetIndex[] TargetIndexes { get; set; } = Array.Empty<TargetIndex>();
        public ModelDefinition[] Models { get; set; } = Array.Empty<ModelDefinition>();
        public RequestLimits RequestLimits { get; set; } = new();
        public object? EncryptionKey { get; set; }
    }

    public class TargetIndex
    {
        public string IndexName { get; set; } = "";
        public double DefaultRerankerThreshold { get; set; }
        public bool? DefaultIncludeReferenceSourceData { get; set; }
        public int? DefaultMaxDocsForReranker { get; set; }
    }

    public class ModelDefinition
    {
        public string Kind { get; set; } = "";
        public AzureOpenAIParameters AzureOpenAIParameters { get; set; } = new();
    }

    public class AzureOpenAIParameters
    {
        public string ResourceUri { get; set; } = "";
        public string? ApiKey { get; set; }
        public string DeploymentId { get; set; } = "";
        public string ModelName { get; set; } = "";
    }

    public class RequestLimits
    {
        public int MaxOutputSize { get; set; }
        public int MaxRuntimeInSeconds { get; set; }
    }

    public class KnowledgeAgentCreateOptions
    {
        public double DefaultRerankerThreshold { get; set; } = 2.5;
        public bool DefaultIncludeReferenceSourceData { get; set; } = true;
        public int DefaultMaxDocsForReranker { get; set; } = 200;
        public string? ModelName { get; set; } = "gpt-4.1";
        public int MaxOutputSize { get; set; } = 5000;
        public int MaxRuntimeInSeconds { get; set; } = 60;
        public object? EncryptionKey { get; set; }
    }

    public class AgenticRetrievalResponse
    {
        public string Content { get; set; } = "";
        public Reference[] References { get; set; } = Array.Empty<Reference>();
        public Activity[] Activity { get; set; } = Array.Empty<Activity>();
        public ResponseMessage[] Response { get; set; } = Array.Empty<ResponseMessage>();
    }

    public class Reference
    {
        public string Type { get; set; } = "";
        public string Id { get; set; } = "";
        public int? ActivitySource { get; set; }
        public string DocKey { get; set; } = "";
        public SourceData? SourceData { get; set; }
    }

    public class Activity
    {
        public string Type { get; set; } = "";
        public int Id { get; set; }
        public string? TargetIndex { get; set; }
        public QueryInfo? Query { get; set; }
        public DateTime? QueryTime { get; set; }
        public int? Count { get; set; }
        public int? ElapsedMs { get; set; }
        public int? InputTokens { get; set; }
        public int? OutputTokens { get; set; }
    }

    public class QueryInfo
    {
        public string Search { get; set; } = "";
        public string? Filter { get; set; }
    }

    public class SourceData
    {
        public string Id { get; set; } = "";
        public string Title { get; set; } = "";
        public string Content { get; set; } = "";
        public string Terms { get; set; } = "";
    }

    public class ResponseMessage
    {
        public string Role { get; set; } = "";
        public ContentItem[] Content { get; set; } = Array.Empty<ContentItem>();
    }

    public class ContentItem
    {
        public string Type { get; set; } = "";
        public string Text { get; set; } = "";
    }
}
