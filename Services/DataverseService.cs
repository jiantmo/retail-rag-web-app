using Microsoft.Identity.Client;
using retail_rag_web_app.Models;
using System.Net.Http.Headers;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using Azure.Core;
using Azure.Identity;

namespace retail_rag_web_app.Services
{
    public class DataverseService
    {
        private readonly HttpClient _httpClient;
        private readonly IConfiguration _configuration;
        private readonly ILogger<DataverseService> _logger;
        private readonly string _auroraOrgUrl;
        private readonly string _auroraOrgUser;
        private readonly string _auroraOrgId;
        private readonly string _dvSearchSkill;
        private readonly string? _clientId;
        
        // Token caching fields
        private static DateTime _tokenExpiryTime = DateTime.MinValue;
        private static readonly object _tokenLock = new object();

        public DataverseService(HttpClient httpClient, IConfiguration configuration, ILogger<DataverseService> logger)
        {
            _httpClient = httpClient;
            _configuration = configuration;
            _logger = logger;
            
            _auroraOrgUrl = _configuration["AURORA_ORG_URL"] ?? throw new ArgumentException("AURORA_ORG_URL not configured");
            _auroraOrgUser = _configuration["AURORA_ORG_USER"] ?? throw new ArgumentException("AURORA_ORG_USER not configured");
            _auroraOrgId = _configuration["AURORA_ORG_ID"] ?? throw new ArgumentException("AURORA_ORG_ID not configured");
            _dvSearchSkill = _configuration["DV_SEARCH_SKILL"] ?? throw new ArgumentException("DV_SEARCH_SKILL not configured");
            _clientId = _configuration["AZURE_CLIENT_ID"]; // Optional
        }

        public async Task<DataverseSearchResponse> SearchAsync(string queryText, string? bearerToken = null)
        {
            try
            {
                _logger.LogInformation("Starting Dataverse search for query: {Query}", queryText);

                // 获取访问令牌
                string accessToken;
                if (!string.IsNullOrWhiteSpace(bearerToken))
                {
                    _logger.LogInformation("Using provided bearer token for authentication");
                    accessToken = bearerToken;
                }
                else
                {
                    _logger.LogError("No bearer token provided for Dataverse search");
                    return new DataverseSearchResponse
                    {
                        Success = false,
                        Error = "Bearer token is required for Dataverse search. Please provide a valid token."
                    };
                }
                
                // 准备请求
                var request = new DataverseSearchRequest
                {
                    QueryText = queryText,
                    Skill = _dvSearchSkill,
                    Options = new List<string> { "GetResultsSummary" },
                    AdditionalProperties = new Dictionary<string, object>
                    {
                        { "ExecuteUnifiedSearch", true }
                    }
                };

                var jsonContent = JsonSerializer.Serialize(request);
                var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

                // 设置请求头
                var requestMessage = new HttpRequestMessage(HttpMethod.Post, $"{_auroraOrgUrl}/api/copilot/v1.0/queryskillstructureddata")
                {
                    Content = content
                };

                requestMessage.Headers.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
                requestMessage.Headers.Add("x-ms-crm-query-language", "1033");
                requestMessage.Headers.Add("x-ms-crm-service-root-url", _auroraOrgUrl);
                requestMessage.Headers.Add("x-ms-crm-userid", _auroraOrgUser);
                requestMessage.Headers.Add("x-ms-organization-id", _auroraOrgId);
                requestMessage.Headers.Add("x-ms-user-agent", "PowerVA/2");

                _logger.LogInformation("Sending request to Dataverse API: {Url}", $"{_auroraOrgUrl}/api/copilot/v1.0/queryskillstructureddata");

                // 发送请求
                var response = await _httpClient.SendAsync(requestMessage);
                var responseContent = await response.Content.ReadAsStringAsync();

                _logger.LogInformation("Dataverse API response status: {StatusCode}", response.StatusCode);
                _logger.LogInformation("Dataverse API response headers: {Headers}", response.Headers.ToString());
                _logger.LogInformation("Dataverse API response content: {Content}", responseContent);

                if (response.IsSuccessStatusCode)
                {
                    // 检查响应内容是否是JSON
                    if (string.IsNullOrWhiteSpace(responseContent) || 
                        responseContent.TrimStart().StartsWith("<") || 
                        responseContent.TrimStart().StartsWith("<!"))
                    {
                        _logger.LogError("Received HTML response instead of JSON. This usually indicates authentication failure or redirect.");
                        return new DataverseSearchResponse
                        {
                            Success = false,
                            Error = "Authentication failed: Received HTML response instead of JSON data"
                        };
                    }

                    // 直接解析Dataverse API的原始响应
                    using var jsonDoc = JsonDocument.Parse(responseContent);
                    var root = jsonDoc.RootElement;
                    
                    // 构建符合我们期望格式的响应
                    var result = new DataverseSearchResponse
                    {
                        Success = true,
                        Error = null
                    };
                    
                    // 检查是否有错误
                    if (root.TryGetProperty("error", out var errorElement) && 
                        errorElement.ValueKind != JsonValueKind.Null)
                    {
                        result.Success = false;
                        result.Error = errorElement.GetString();
                        return result;
                    }
                    
                    // 提取summary和results
                    if (root.TryGetProperty("queryResult", out var queryResultElement))
                    {
                        if (queryResultElement.TryGetProperty("summary", out var summaryElement))
                        {
                            result.Summary = summaryElement.GetString();
                        }
                        
                        // 存储完整的Dataverse API响应作为一个自定义属性
                        // 这样前端可以访问所有原始数据
                        result.RawApiResponse = responseContent;
                    }
                    
                    return result;
                }

                return new DataverseSearchResponse
                {
                    Success = false,
                    Error = $"API request failed with status {response.StatusCode}: {responseContent}"
                };
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error occurred during Dataverse search");
                return new DataverseSearchResponse
                {
                    Success = false,
                    Error = $"Search failed: {ex.Message}"
                };
            }
        }
    }
}
