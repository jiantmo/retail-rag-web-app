using Azure.AI.OpenAI;
using Azure.Identity;
using Azure.Search.Documents;
using Azure.Search.Documents.Models;
using OpenAI.Chat;
using System.Text.Json;
using Azure;
using Azure.Core;

namespace retail_rag_web_app.Services
{
    public class RagService
    {
        private readonly SearchClient _searchClient;
        private readonly AzureOpenAIClient _openAIClient;
        private readonly ChatClient _chatClient;
        private readonly string _indexName;
        private readonly ILogger<RagService> _logger;
        
        private readonly string GROUNDED_PROMPT = @"You are a friendly retail assistant that helps customers find products and answers their questions.
Answer the query using only the sources provided below in a friendly and helpful manner.
Answer ONLY with the facts listed in the list of sources below.
If there isn't enough information below, say you don't know.
Do not generate answers that don't use the sources below.
Query: {0}
Sources: {1}";

        public RagService(IConfiguration configuration, ILogger<RagService> logger)
        {
            _logger = logger;
            
            var searchEndpoint = configuration["AZURE_SEARCH_ENDPOINT"] 
                ?? throw new ArgumentException("AZURE_SEARCH_ENDPOINT not configured");
            var openAIEndpoint = configuration["AZURE_OPENAI_ENDPOINT"]
                ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT not configured");
            var gptDeployment = configuration["AZURE_OPENAI_GPT_DEPLOYMENT"]
                ?? throw new ArgumentException("AZURE_OPENAI_GPT_DEPLOYMENT not configured");
            var managedIdentityClientId = Environment.GetEnvironmentVariable("AZURE_CLIENT_ID") 
                ?? configuration["AzureManagedIdentity:ClientId"];
            _indexName = configuration["AZURE_SEARCH_INDEX_NAME"]
                ?? throw new ArgumentException("AZURE_SEARCH_INDEX_NAME not configured");

            _logger.LogInformation("Initializing RagService with Search: {SearchEndpoint}, OpenAI: {OpenAIEndpoint}, Index: {IndexName}", 
                searchEndpoint, openAIEndpoint, _indexName);

            // 使用Managed Identity或DefaultAzureCredential认证
            TokenCredential credential;
            if (!string.IsNullOrEmpty(managedIdentityClientId))
            {
                _logger.LogInformation("Using ManagedIdentityCredential with ClientId: {ClientId}", managedIdentityClientId);
                credential = new ManagedIdentityCredential(managedIdentityClientId);
            }
            else
            {
                _logger.LogInformation("Using DefaultAzureCredential");
                credential = new DefaultAzureCredential();
            }
            
            _searchClient = new SearchClient(new Uri(searchEndpoint), _indexName, credential);
            _openAIClient = new AzureOpenAIClient(new Uri(openAIEndpoint), credential);
            _chatClient = _openAIClient.GetChatClient(gptDeployment);
            
            _logger.LogInformation("RagService initialized successfully");
        }

        public async Task<string> SearchAsync(string query)
        {
            try
            {
                _logger.LogInformation("Starting search for query: {Query}", query);
                
                // 基于微软官方示例的简化配置
                var options = new SearchOptions 
                { 
                    Size = 5
                };
                
                // 先测试不指定字段，让Azure Search自动选择所有可检索字段
                _logger.LogInformation("Executing search against index: {IndexName}", _indexName);
                
                // 执行搜索 - 按照官方示例的简单格式
                var searchResults = await _searchClient.SearchAsync<SearchDocument>(query, options);
                var sources = new List<string>();

                _logger.LogInformation("Search completed, processing results...");

                await foreach (var result in searchResults.Value.GetResultsAsync())
                {
                    var doc = result.Document;
                    
                    _logger.LogInformation("Found result with {FieldCount} fields. Score: {Score}", 
                        doc.Count, result.Score);
                    
                    // 记录所有可用字段（只显示前100个字符避免日志过长）
                    foreach (var field in doc)
                    {
                        var fieldValuePreview = field.Value?.ToString()?.Substring(0, Math.Min(100, field.Value?.ToString()?.Length ?? 0));
                        _logger.LogInformation("Available field: {FieldName} = {FieldValue}...", 
                            field.Key, fieldValuePreview);
                    }
                    
                    // 尝试获取常见的字段并格式化为源
                    var source = FormatDocumentAsSource(doc);
                    if (!string.IsNullOrEmpty(source))
                    {
                        sources.Add(source);
                        _logger.LogInformation("Added source with length: {SourceLength}", source.Length);
                    }
                }

                _logger.LogInformation("Total sources found: {SourceCount}", sources.Count);

                if (!sources.Any())
                {
                    _logger.LogWarning("No sources found for query: {Query}", query);
                    return "I couldn't find any relevant information for your query. Please try rephrasing your question.";
                }

                string sourcesFormatted = string.Join("\n\n", sources);
                _logger.LogInformation("Formatted sources length: {SourcesLength}", sourcesFormatted.Length);

                // 格式化提示词
                string formattedPrompt = string.Format(GROUNDED_PROMPT, query, sourcesFormatted);

                // 按照官方示例使用ChatMessage列表
                List<ChatMessage> messages = new List<ChatMessage>()
                {
                    new SystemChatMessage("You are a friendly retail assistant that helps customers find products."),
                    new UserChatMessage(formattedPrompt)
                };

                // 发送到OpenAI并获取响应
                _logger.LogInformation("Sending request to OpenAI...");
                var response = await _chatClient.CompleteChatAsync(messages);
                
                _logger.LogInformation("OpenAI response received successfully");
                return response.Value.Content[0].Text;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error occurred during search: {ErrorMessage}", ex.Message);
                return $"Error occurred while processing your request: {ex.Message}";
            }
        }

        private string FormatDocumentAsSource(SearchDocument doc)
        {
            try
            {
                var source = new System.Text.StringBuilder();
                
                // 尝试常见的字段名称
                var commonFields = new[] { "chunk", "content", "text", "description", "title", "name" };
                
                foreach (var fieldName in commonFields)
                {
                    if (doc.TryGetValue(fieldName, out var fieldValue) && fieldValue != null)
                    {
                        var valueStr = fieldValue.ToString();
                        if (!string.IsNullOrEmpty(valueStr))
                        {
                            source.AppendLine($"{fieldName}: {valueStr}");
                        }
                    }
                }
                
                // 如果没有找到常见字段，使用所有字段
                if (source.Length == 0)
                {
                    foreach (var field in doc)
                    {
                        if (field.Value != null && !string.IsNullOrEmpty(field.Value.ToString()))
                        {
                            source.AppendLine($"{field.Key}: {field.Value}");
                        }
                    }
                }
                
                return source.ToString();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error formatting document as source");
                return doc.ToString();
            }
        }

        public async IAsyncEnumerable<string> SearchStreamRealTimeAsync(string query)
        {
            // 不能在try-catch中使用yield，所以我们需要分离异常处理
            IAsyncEnumerable<string> streamResults;
            
            try
            {
                streamResults = StreamSearchInternal(query);
            }
            catch (Exception ex)
            {
                streamResults = StreamError($"Error occurred while processing your request: {ex.Message}");
            }
            
            await foreach (var result in streamResults)
            {
                yield return result;
            }
        }

        private async IAsyncEnumerable<string> StreamSearchInternal(string query)
        {
            // 先执行搜索部分
            var options = new SearchOptions 
            { 
                Size = 5
            };
            
            var searchResults = await _searchClient.SearchAsync<SearchDocument>(query, options);
            var sources = new List<string>();

            await foreach (var result in searchResults.Value.GetResultsAsync())
            {
                var doc = result.Document;
                var source = FormatDocumentAsSource(doc);
                
                if (!string.IsNullOrEmpty(source))
                {
                    sources.Add(source);
                }
            }

            if (!sources.Any())
            {
                yield return "I couldn't find any relevant information for your query.";
                yield break;
            }

            string sourcesFormatted = string.Join("\n\n", sources);
            string formattedPrompt = string.Format(GROUNDED_PROMPT, query, sourcesFormatted);

            List<ChatMessage> messages = new List<ChatMessage>()
            {
                new SystemChatMessage("You are a friendly retail assistant that helps customers find products."),
                new UserChatMessage(formattedPrompt)
            };

            // 真正的流式响应 - 逐步yield每个token
            var chatUpdates = _chatClient.CompleteChatStreamingAsync(messages);
            
            await foreach (var chatUpdate in chatUpdates)
            {
                foreach (var contentPart in chatUpdate.ContentUpdate)
                {
                    if (!string.IsNullOrEmpty(contentPart.Text))
                    {
                        yield return contentPart.Text;
                    }
                }
            }
        }

        private async IAsyncEnumerable<string> StreamError(string errorMessage)
        {
            yield return errorMessage;
            await Task.CompletedTask; // 满足async要求
        }
    }
}