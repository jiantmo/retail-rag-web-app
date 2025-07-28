using Azure.Identity;
using Azure.Search.Documents.Indexes;
using Azure.Search.Documents.Indexes.Models;
using System.Text.Json;
using Azure.Core;
using Microsoft.Extensions.Logging;

namespace retail_rag_web_app.Services
{
    /// <summary>
    /// Enhanced Knowledge Agent Service specifically for retail scenarios
    /// Implements agentic retrieval using the official Azure Search Knowledge Agent API
    /// </summary>
    public class KnowledgeAgentService_Enhanced
    {
        private readonly SearchIndexClient _indexClient;
        private readonly ILogger<KnowledgeAgentService_Enhanced> _logger;
        private readonly string _searchEndpoint;
        private readonly string _openAIEndpoint;
        private readonly string _gptDeployment;
        private readonly string _indexName;
        private readonly string _agentName;

        public KnowledgeAgentService_Enhanced(IConfiguration configuration, ILogger<KnowledgeAgentService_Enhanced> logger)
        {
            _logger = logger;
            
            _searchEndpoint = configuration["AZURE_SEARCH_ENDPOINT"] 
                ?? throw new ArgumentException("AZURE_SEARCH_ENDPOINT not configured");
            _openAIEndpoint = configuration["AZURE_OPENAI_ENDPOINT"]
                ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT not configured");
            _gptDeployment = configuration["AZURE_OPENAI_GPT_DEPLOYMENT"]
                ?? throw new ArgumentException("AZURE_OPENAI_GPT_DEPLOYMENT not configured");
            _indexName = configuration["AZURE_SEARCH_INDEX_NAME"]
                ?? throw new ArgumentException("AZURE_SEARCH_INDEX_NAME not configured");
            _agentName = configuration["AZURE_SEARCH_AGENT_NAME"]
                ?? "retail-knowledge-agent";

            // 使用System-assigned Managed Identity认证
            TokenCredential credential = new DefaultAzureCredential(new DefaultAzureCredentialOptions
            {
                ManagedIdentityClientId = null // Use system-assigned managed identity
            });
            
            _indexClient = new SearchIndexClient(new Uri(_searchEndpoint), credential);
            
            _logger.LogInformation("Enhanced KnowledgeAgentService initialized. Agent: {AgentName}, Index: {IndexName}, Deployment: {Deployment}", 
                _agentName, _indexName, _gptDeployment);
        }

        /// <summary>
        /// 创建优化的零售知识代理 
        /// </summary>
        public async Task<bool> CreateRetailKnowledgeAgentAsync()
        {
            try
            {
                _logger.LogInformation("Creating enhanced retail knowledge agent: {AgentName}", _agentName);

                // 检查索引是否存在
                if (!await CheckIndexExistsAsync())
                {
                    _logger.LogError("Search index {IndexName} does not exist", _indexName);
                    return false;
                }

                // 创建知识代理定义 - 使用最新的 Azure Search Documents SDK
                var agent = new KnowledgeAgent(
                    name: _agentName,
                    models: new[] 
                    { 
                        new KnowledgeAgentAzureOpenAIModel(
                            azureOpenAIParameters: new AzureOpenAIVectorizerParameters
                            {
                                ResourceUri = new Uri(_openAIEndpoint),
                                DeploymentName = _gptDeployment,
                                ModelName = _gptDeployment == "gpt-4.1" ? "gpt-4.1" : "gpt-4o-mini"
                            }
                        )
                    },
                    targetIndexes: new[] 
                    { 
                        new KnowledgeAgentTargetIndex(_indexName)
                        {
                            DefaultRerankerThreshold = 1.8f, // 降低阈值以提高召回率
                            DefaultMaxDocsForReranker = 200,  // 增加候选文档数
                            DefaultIncludeReferenceSourceData = true
                        }
                    }
                );

                await _indexClient.CreateOrUpdateKnowledgeAgentAsync(agent);
                
                _logger.LogInformation("Enhanced retail knowledge agent '{AgentName}' created successfully", _agentName);
                return true;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error creating enhanced knowledge agent '{AgentName}': {ErrorMessage}", _agentName, ex.Message);
                return false;
            }
        }

        /// <summary>
        /// 执行增强的代理检索
        /// </summary>
        public async Task<AgenticRetrievalResult> RetrieveAsync(string query, string? systemPrompt = null)
        {
            try
            {
                _logger.LogInformation("Executing enhanced agentic retrieval for query: {Query}", query);

                // 创建知识代理检索客户端
                var credential = new DefaultAzureCredential(new DefaultAzureCredentialOptions
                {
                    ManagedIdentityClientId = null
                });

                var agentClient = new KnowledgeAgentRetrievalClient(
                    endpoint: new Uri(_searchEndpoint),
                    agentName: _agentName,
                    tokenCredential: credential
                );

                // 构建消息
                var messages = new List<KnowledgeAgentMessage>();

                // 添加系统提示（可选）
                if (!string.IsNullOrEmpty(systemPrompt))
                {
                    messages.Add(new KnowledgeAgentMessage(
                        role: "system",
                        content: new[] { new KnowledgeAgentMessageTextContent(systemPrompt) }
                    ));
                }

                // 添加用户查询
                messages.Add(new KnowledgeAgentMessage(
                    role: "user",
                    content: new[] { new KnowledgeAgentMessageTextContent(query) }
                ));

                // 执行检索
                var retrievalRequest = new KnowledgeAgentRetrievalRequest(messages)
                {
                    TargetIndexParams = { new KnowledgeAgentIndexParams 
                    { 
                        IndexName = _indexName, 
                        RerankerThreshold = 1.8f,
                        MaxDocsForReranker = 200,
                        IncludeReferenceSourceData = true
                    } }
                };

                var result = await agentClient.RetrieveAsync(retrievalRequest);

                _logger.LogInformation("Enhanced agentic retrieval completed. References: {RefCount}, Activities: {ActCount}", 
                    result.Value.References?.Count ?? 0, result.Value.Activity?.Count ?? 0);

                return new AgenticRetrievalResult
                {
                    Success = true,
                    Response = ExtractResponseText(result.Value.Response),
                    References = result.Value.References?.ToList() ?? new List<KnowledgeAgentReference>(),
                    Activity = result.Value.Activity?.ToList() ?? new List<KnowledgeAgentActivity>(),
                    RawResult = result.Value
                };
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error during enhanced agentic retrieval: {ErrorMessage}", ex.Message);
                return new AgenticRetrievalResult
                {
                    Success = false,
                    ErrorMessage = ex.Message
                };
            }
        }

        /// <summary>
        /// 检查知识代理是否存在
        /// </summary>
        public async Task<bool> AgentExistsAsync()
        {
            try
            {
                var agent = await _indexClient.GetKnowledgeAgentAsync(_agentName);
                return agent != null;
            }
            catch (Exception)
            {
                return false;
            }
        }

        /// <summary>
        /// 删除知识代理
        /// </summary>
        public async Task<bool> DeleteAgentAsync()
        {
            try
            {
                await _indexClient.DeleteKnowledgeAgentAsync(_agentName);
                _logger.LogInformation("Knowledge agent '{AgentName}' deleted successfully", _agentName);
                return true;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error deleting knowledge agent '{AgentName}': {ErrorMessage}", _agentName, ex.Message);
                return false;
            }
        }

        private async Task<bool> CheckIndexExistsAsync()
        {
            try
            {
                var index = await _indexClient.GetIndexAsync(_indexName);
                return index != null;
            }
            catch (Exception)
            {
                return false;
            }
        }

        private string ExtractResponseText(IReadOnlyList<ResponseMessage>? responses)
        {
            if (responses == null || responses.Count == 0)
                return string.Empty;

            var texts = new List<string>();
            foreach (var response in responses)
            {
                foreach (var content in response.Content)
                {
                    if (content.Type == "text")
                    {
                        texts.Add(content.Text);
                    }
                }
            }

            return string.Join("\n", texts);
        }
    }

    /// <summary>
    /// 增强的代理检索结果
    /// </summary>
    public class AgenticRetrievalResult
    {
        public bool Success { get; set; }
        public string Response { get; set; } = string.Empty;
        public string? ErrorMessage { get; set; }
        public List<Reference> References { get; set; } = new();
        public List<Activity> Activity { get; set; } = new();
        public object? RawResult { get; set; }
    }
}
