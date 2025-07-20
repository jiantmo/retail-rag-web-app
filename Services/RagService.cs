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
        
        private readonly string GROUNDED_PROMPT = @"You are a friendly retail assistant that helps customers find products and answers their questions.
Answer the query using only the sources provided below in a friendly and helpful manner.
Answer ONLY with the facts listed in the list of sources below.
If there isn't enough information below, say you don't know.
Do not generate answers that don't use the sources below.
Query: {0}
Sources: {1}";

        public RagService(IConfiguration configuration)
        {
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

            // 使用Managed Identity或DefaultAzureCredential认证
            TokenCredential credential;
            if (!string.IsNullOrEmpty(managedIdentityClientId))
            {
                credential = new ManagedIdentityCredential(managedIdentityClientId);
            }
            else
            {
                credential = new DefaultAzureCredential();
            }
            
            _searchClient = new SearchClient(new Uri(searchEndpoint), _indexName, credential);
            _openAIClient = new AzureOpenAIClient(new Uri(openAIEndpoint), credential);
            _chatClient = _openAIClient.GetChatClient(gptDeployment);
        }

        public async Task<string> SearchAsync(string query)
        {
            try
            {
                // 配置搜索选项
                var options = new SearchOptions 
                { 
                    Size = 5,
                    QueryType = SearchQueryType.Simple // 使用简单查询类型
                };
                
                // 只选择实际存在的字段
                options.Select.Add("chunk");         // 包含完整产品信息的主要字段
                options.Select.Add("chunk_id");      // 用于调试（可选）
                
                // 执行搜索
                var searchResults = await _searchClient.SearchAsync<SearchDocument>(query, options);
                var sources = new List<string>();

                await foreach (var result in searchResults.Value.GetResultsAsync())
                {
                    var doc = result.Document;
                    
                    // 获取chunk内容（已包含格式化的产品信息）
                    var chunk = doc.TryGetValue("chunk", out var chunkObj) ? chunkObj?.ToString() : "";
                    var chunkId = doc.TryGetValue("chunk_id", out var idObj) ? idObj?.ToString() : "";
                    
                    if (!string.IsNullOrEmpty(chunk))
                    {
                        // 解析chunk中的结构化信息
                        var productInfo = ParseProductInfo(chunk);
                        sources.Add(productInfo);
                    }
                }

                if (!sources.Any())
                {
                    return "I couldn't find any relevant information for your query. Please try rephrasing your question.";
                }

                string sourcesFormatted = string.Join("\n\n", sources);

                // 格式化提示词
                string formattedPrompt = string.Format(GROUNDED_PROMPT, query, sourcesFormatted);

                // 按照官方示例使用ChatMessage列表
                List<ChatMessage> messages = new List<ChatMessage>()
                {
                    new SystemChatMessage("You are a friendly retail assistant that helps customers find products."),
                    new UserChatMessage(formattedPrompt)
                };

                // 发送到OpenAI并获取响应
                var response = await _chatClient.CompleteChatAsync(messages);

                return response.Value.Content[0].Text;
            }
            catch (Exception ex)
            {
                return $"Error occurred while processing your request: {ex.Message}";
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
                Size = 5,
                QueryType = SearchQueryType.Simple
            };
            
            options.Select.Add("chunk");
            options.Select.Add("chunk_id");
            
            var searchResults = await _searchClient.SearchAsync<SearchDocument>(query, options);
            var sources = new List<string>();

            await foreach (var result in searchResults.Value.GetResultsAsync())
            {
                var doc = result.Document;
                var chunk = doc.TryGetValue("chunk", out var chunkObj) ? chunkObj?.ToString() : "";
                
                if (!string.IsNullOrEmpty(chunk))
                {
                    var productInfo = ParseProductInfo(chunk);
                    sources.Add(productInfo);
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

        private string ParseProductInfo(string chunk)
        {
            // chunk格式示例: "Name: Vareno Compact Surfboard; Price: 638.77; TotalRatings: 4053; Description: Designed with a rela..."
            
            var productInfo = new System.Text.StringBuilder();
            productInfo.AppendLine("Product Details:");
            
            try
            {
                // 使用分号分割字段
                var fields = chunk.Split(';', StringSplitOptions.RemoveEmptyEntries);
                
                foreach (var field in fields)
                {
                    var keyValue = field.Split(':', 2, StringSplitOptions.RemoveEmptyEntries);
                    if (keyValue.Length == 2)
                    {
                        var key = keyValue[0].Trim();
                        var value = keyValue[1].Trim();
                        
                        // 显示所有字段，保持原始格式
                        productInfo.AppendLine($"• {key}: {value}");
                    }
                    else
                    {
                        // 如果没有冒号分隔符，直接显示整个字段
                        productInfo.AppendLine($"• {field.Trim()}");
                    }
                }
                
                return productInfo.ToString();
            }
            catch (Exception)
            {
                // 如果解析失败，返回原始chunk但格式化显示
                return $"Product Information:\n• {chunk}";
            }
        }
    }
}
