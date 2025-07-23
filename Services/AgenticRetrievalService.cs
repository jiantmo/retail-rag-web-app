using Azure;
using Azure.Core;
using Azure.Identity;
using Azure.Search.Documents;
using Azure.Search.Documents.Indexes;
using Azure.Search.Documents.Models;
using System.Text.Json;
using System.Text.RegularExpressions;
using dotenv.net;
using retail_rag_web_app.Models;

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
                ?? "rag-acs-index";

            _openAIEndpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") 
                ?? configuration["AZURE_OPENAI_ENDPOINT"] 
                ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT not configured");

            _openAIDeployment = Environment.GetEnvironmentVariable("AZURE_OPENAI_GPT_DEPLOYMENT") 
                ?? configuration["AZURE_OPENAI_GPT_DEPLOYMENT"] 
                ?? "gpt-4.1";

            // Use System-assigned Managed Identity for authentication
            _credential = new DefaultAzureCredential(new DefaultAzureCredentialOptions
            {
                ManagedIdentityClientId = null // Use system-assigned managed identity
            });
            _logger.LogInformation("Using DefaultAzureCredential with system-assigned managed identity");

            _logger.LogInformation("AgenticRetrievalService initialized with endpoint: {Endpoint}, agent: {Agent}, index: {Index}", 
                _searchEndpoint, _agentName, _indexName);
        }

        public async Task<string> CreateKnowledgeAgentAsync()
        {
            try
            {
                _logger.LogInformation("Creating knowledge agent: {AgentName}", _agentName);

                var agentDefinition = new
                {
                    name = _agentName,
                    description = "Retail product recommendation agent with advanced query planning",
                    targetIndexes = new[]
                    {
                        new
                        {
                            indexName = _indexName,
                            defaultRerankerThreshold = 1.5,  // Lower threshold for better recall
                            defaultIncludeReferenceSourceData = true,
                            defaultMaxDocsForReranker = 300
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
                                deploymentId = _openAIDeployment,
                                modelName = "gpt-4.1"
                            }
                        }
                    }
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

        public async Task<AgenticSearchFormattedResponse> AgenticRetrieveFormattedAsync(string userQuery, string? systemPrompt = null)
        {
            try
            {
                _logger.LogInformation("Starting formatted agentic retrieval for query: {Query}", userQuery);

                // Get raw response from Azure AI Search
                var rawResponse = await AgenticRetrieveAsync(userQuery, systemPrompt);
                
                // Parse and format the response
                var formattedResponse = ParseAndFormatResponse(rawResponse);
                formattedResponse.RawResponse = rawResponse;
                
                _logger.LogInformation("Formatted agentic retrieval completed. IsProductList: {IsProductList}, ProductCount: {ProductCount}", 
                    formattedResponse.IsProductList, formattedResponse.Products.Count);
                
                return formattedResponse;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in formatted agentic retrieval for query: {Query}", userQuery);
                
                // Return a fallback response with the error
                return new AgenticSearchFormattedResponse
                {
                    IsProductList = false,
                    FormattedText = $"Error processing search request: {ex.Message}",
                    RawResponse = ex.ToString()
                };
            }
        }

        private AgenticSearchFormattedResponse ParseAndFormatResponse(string rawResponse)
        {
            var response = new AgenticSearchFormattedResponse();
            
            try
            {
                _logger.LogInformation("Parsing raw response (length: {Length})", rawResponse.Length);
                
                var jsonDocument = JsonDocument.Parse(rawResponse);
                var root = jsonDocument.RootElement;
                
                _logger.LogInformation("Raw response parsed successfully");
                
                // Check if this is a product list response by looking for arrays with ref_id fields
                var products = new List<ProductResult>();
                bool foundProductArray = false;
                
                // Look for arrays in the response that might contain products
                if (root.ValueKind == JsonValueKind.Array)
                {
                    _logger.LogInformation("Root is array with {Count} elements", root.GetArrayLength());
                    foundProductArray = TryParseProductArray(root, products);
                }
                else if (root.ValueKind == JsonValueKind.Object)
                {
                    // Look for arrays within the object
                    foreach (var property in root.EnumerateObject())
                    {
                        if (property.Value.ValueKind == JsonValueKind.Array)
                        {
                            _logger.LogInformation("Found array property: {PropertyName} with {Count} elements", 
                                property.Name, property.Value.GetArrayLength());
                            
                            if (TryParseProductArray(property.Value, products))
                            {
                                foundProductArray = true;
                                break;
                            }
                        }
                    }
                    
                    // If no product array found, try to extract response text
                    if (!foundProductArray)
                    {
                        response.FormattedText = ExtractResponseText(root);
                        ExtractActivityAndReferences(root, response);
                    }
                }
                
                if (foundProductArray && products.Any())
                {
                    response.IsProductList = true;
                    response.Products = products;
                    response.ActivityInfo = $"Found {products.Count} relevant product(s) ranked by relevance and similarity";
                    _logger.LogInformation("Successfully parsed {Count} products", products.Count);
                }
                else if (string.IsNullOrEmpty(response.FormattedText))
                {
                    // Fallback: try to extract any meaningful text from the response
                    response.FormattedText = ExtractAnyText(rawResponse);
                }
                
            }
            catch (JsonException ex)
            {
                _logger.LogError(ex, "Failed to parse JSON response");
                response.FormattedText = "Error: Unable to parse search response. Please try a different query.";
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing response");
                response.FormattedText = $"Error processing response: {ex.Message}";
            }
            
            return response;
        }

        private bool TryParseProductArray(JsonElement arrayElement, List<ProductResult> products)
        {
            try
            {
                if (arrayElement.ValueKind != JsonValueKind.Array)
                    return false;
                
                bool hasProductLikeElements = false;
                
                foreach (var element in arrayElement.EnumerateArray())
                {
                    if (element.ValueKind == JsonValueKind.Object)
                    {
                        var hasRefId = element.TryGetProperty("ref_id", out _);
                        var hasContent = element.TryGetProperty("content", out _);
                        var hasTitle = element.TryGetProperty("title", out _);
                        
                        // Check if this looks like a product element
                        if (hasRefId || hasContent || hasTitle)
                        {
                            var product = ParseProduct(element);
                            if (product != null)
                            {
                                products.Add(product);
                                hasProductLikeElements = true;
                            }
                        }
                    }
                }
                
                return hasProductLikeElements;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error parsing product array");
                return false;
            }
        }

        private ProductResult? ParseProduct(JsonElement productElement)
        {
            try
            {
                var product = new ProductResult();
                
                // Get basic fields
                if (productElement.TryGetProperty("ref_id", out var refIdElement))
                {
                    product.RefId = refIdElement.GetString() ?? "";
                }
                
                if (productElement.TryGetProperty("title", out var titleElement))
                {
                    product.Name = titleElement.GetString() ?? "Unknown Product";
                }
                
                // Parse content field which contains detailed product info
                if (productElement.TryGetProperty("content", out var contentElement))
                {
                    var content = contentElement.GetString() ?? "";
                    ParseProductContent(content, product);
                }
                
                // Only return if we have meaningful data
                if (!string.IsNullOrEmpty(product.Name) || !string.IsNullOrEmpty(product.Description))
                {
                    return product;
                }
                
                return null;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error parsing individual product");
                return null;
            }
        }

        private void ParseProductContent(string content, ProductResult product)
        {
            try
            {
                // Extract basic product info using regex
                var nameMatch = Regex.Match(content, @"Name:\s*([^;]+)", RegexOptions.IgnoreCase);
                if (nameMatch.Success && string.IsNullOrEmpty(product.Name))
                {
                    product.Name = nameMatch.Groups[1].Value.Trim();
                }
                
                var priceMatch = Regex.Match(content, @"Price:\s*([0-9.]+)", RegexOptions.IgnoreCase);
                if (priceMatch.Success)
                {
                    if (decimal.TryParse(priceMatch.Groups[1].Value, out var price))
                    {
                        product.Price = price;
                    }
                }
                
                var productNumberMatch = Regex.Match(content, @"ProductNumber:\s*([^;]+)", RegexOptions.IgnoreCase);
                if (productNumberMatch.Success)
                {
                    product.ProductNumber = productNumberMatch.Groups[1].Value.Trim();
                }
                
                var descriptionMatch = Regex.Match(content, @"Description:\s*([^;]+)", RegexOptions.IgnoreCase);
                if (descriptionMatch.Success)
                {
                    product.Description = descriptionMatch.Groups[1].Value.Trim();
                }
                
                // Extract attributes
                var colorMatches = Regex.Matches(content, @"'Name':\s*'Color'.*?'TextValue':\s*'([^']+)'", RegexOptions.IgnoreCase);
                if (colorMatches.Count > 0)
                {
                    product.Color = colorMatches[0].Groups[1].Value;
                }
                
                var sizeMatches = Regex.Matches(content, @"'Name':\s*'Size'.*?'TextValue':\s*'([^']+)'", RegexOptions.IgnoreCase);
                if (sizeMatches.Count > 0)
                {
                    product.Size = sizeMatches[0].Groups[1].Value.Replace("|", ", ");
                }
                
                var materialMatches = Regex.Matches(content, @"'Name':\s*'AW\s*(Material|Fabric)'.*?'TextValue':\s*'([^']+)'", RegexOptions.IgnoreCase);
                if (materialMatches.Count > 0)
                {
                    product.Material = materialMatches[0].Groups[2].Value;
                }
                
                // Extract product images
                var imageMatches = Regex.Matches(content, @"'([^']*\.png)'", RegexOptions.IgnoreCase);
                foreach (Match match in imageMatches)
                {
                    var imageUrl = match.Groups[1].Value;
                    if (!string.IsNullOrEmpty(imageUrl) && !product.ImageUrls.Contains(imageUrl))
                    {
                        product.ImageUrls.Add(imageUrl);
                    }
                }
                
                _logger.LogDebug("Parsed product: {Name}, Price: {Price}, Images: {ImageCount}", 
                    product.Name, product.Price, product.ImageUrls.Count);
                    
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error parsing product content");
            }
        }

        private string ExtractResponseText(JsonElement root)
        {
            try
            {
                // Try to find response text in various possible locations
                if (root.TryGetProperty("response", out var responseArray) && responseArray.ValueKind == JsonValueKind.Array)
                {
                    foreach (var response in responseArray.EnumerateArray())
                    {
                        if (response.TryGetProperty("role", out var role) && role.GetString() == "assistant")
                        {
                            if (response.TryGetProperty("content", out var contentArray) && contentArray.ValueKind == JsonValueKind.Array)
                            {
                                foreach (var content in contentArray.EnumerateArray())
                                {
                                    if (content.TryGetProperty("text", out var text))
                                    {
                                        return text.GetString() ?? "";
                                    }
                                }
                            }
                        }
                    }
                }
                
                // Try choices format (OpenAI style)
                if (root.TryGetProperty("choices", out var choicesArray) && choicesArray.ValueKind == JsonValueKind.Array)
                {
                    foreach (var choice in choicesArray.EnumerateArray())
                    {
                        if (choice.TryGetProperty("message", out var message))
                        {
                            if (message.TryGetProperty("content", out var content))
                            {
                                return content.GetString() ?? "";
                            }
                        }
                    }
                }
                
                // Try direct answer fields
                if (root.TryGetProperty("answer", out var answer))
                {
                    return answer.GetString() ?? "";
                }
                
                if (root.TryGetProperty("text", out var textField))
                {
                    return textField.GetString() ?? "";
                }
                
                return "";
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error extracting response text");
                return "";
            }
        }

        private void ExtractActivityAndReferences(JsonElement root, AgenticSearchFormattedResponse response)
        {
            try
            {
                _logger.LogInformation("🔍 Starting ExtractActivityAndReferences");
                
                // Extract activity information following Microsoft's agentic retrieval format
                if (root.TryGetProperty("activity", out var activity) && activity.ValueKind == JsonValueKind.Array)
                {
                    var planningActivities = 0;
                    var searchActivities = 0;
                    var semanticRankerActivities = 0;
                    var totalActivities = activity.GetArrayLength();
                    var subQueries = new List<SubQueryResult>();
                    int planningInputTokens = 0;
                    int planningOutputTokens = 0;
                    
                    _logger.LogInformation("📊 Processing {Count} activity items", totalActivities);
                    
                    foreach (var activityItem in activity.EnumerateArray())
                    {
                        _logger.LogDebug("🔎 Processing activity item: {Activity}", activityItem.GetRawText());
                        
                        if (activityItem.TryGetProperty("type", out var type))
                        {
                            var typeStr = type.GetString() ?? "";
                            _logger.LogDebug("📋 Activity type: {Type}", typeStr);
                            
                            // Handle ModelQueryPlanning activities (based on Microsoft docs)
                            if (typeStr.Equals("ModelQueryPlanning", StringComparison.OrdinalIgnoreCase) || 
                                typeStr.Contains("Planning"))
                            {
                                planningActivities++;
                                _logger.LogDebug("🧠 Found planning activity");
                                
                                // Extract planning token usage
                                if (activityItem.TryGetProperty("inputTokens", out var inputTokens))
                                {
                                    planningInputTokens = inputTokens.GetInt32();
                                }
                                if (activityItem.TryGetProperty("outputTokens", out var outputTokens))
                                {
                                    planningOutputTokens = outputTokens.GetInt32();
                                }
                                
                                response.QueryPlanningTokens = $"Input: {planningInputTokens}, Output: {planningOutputTokens}";
                                _logger.LogDebug("💭 Planning tokens: {Tokens}", response.QueryPlanningTokens);
                            }
                            // Handle AzureSearchQuery activities (sub-queries from Microsoft docs)
                            else if (typeStr.Equals("AzureSearchQuery", StringComparison.OrdinalIgnoreCase) || 
                                     typeStr.Contains("Search"))
                            {
                                searchActivities++;
                                _logger.LogDebug("🔍 Found search activity");
                                
                                // Extract sub-query details following Microsoft's format
                                var subQuery = new SubQueryResult();
                                
                                // Get target index
                                if (activityItem.TryGetProperty("targetIndex", out var targetIndex))
                                {
                                    _logger.LogDebug("🎯 Target index: {Index}", targetIndex.GetString());
                                }
                                
                                // Extract query object
                                if (activityItem.TryGetProperty("query", out var queryObj))
                                {
                                    if (queryObj.TryGetProperty("search", out var searchText))
                                    {
                                        subQuery.Query = searchText.GetString() ?? "";
                                        _logger.LogDebug("🔎 Sub-query: {Query}", subQuery.Query);
                                    }
                                    
                                    if (queryObj.TryGetProperty("filter", out var filterText) && 
                                        filterText.ValueKind != JsonValueKind.Null)
                                    {
                                        subQuery.Filter = filterText.GetString();
                                        _logger.LogDebug("🔧 Filter: {Filter}", subQuery.Filter);
                                    }
                                }
                                
                                // Extract timing and results
                                if (activityItem.TryGetProperty("count", out var count))
                                {
                                    subQuery.ResultCount = count.GetInt32();
                                    _logger.LogDebug("📊 Result count: {Count}", subQuery.ResultCount);
                                }
                                
                                if (activityItem.TryGetProperty("elapsedMs", out var elapsed))
                                {
                                    subQuery.ElapsedMs = elapsed.GetInt32();
                                    _logger.LogDebug("⏱️ Elapsed ms: {ElapsedMs}", subQuery.ElapsedMs);
                                }
                                
                                if (activityItem.TryGetProperty("queryTime", out var queryTime) && 
                                    DateTime.TryParse(queryTime.GetString(), out var parsedTime))
                                {
                                    subQuery.QueryTime = parsedTime;
                                    _logger.LogDebug("🕒 Query time: {QueryTime}", subQuery.QueryTime);
                                }
                                
                                // Add sub-query if it has meaningful content
                                if (!string.IsNullOrEmpty(subQuery.Query))
                                {
                                    subQueries.Add(subQuery);
                                    _logger.LogDebug("✅ Added sub-query: {Query}", subQuery.Query);
                                }
                            }
                            // Handle SemanticRanker activities
                            else if (typeStr.Equals("AzureSearchSemanticRanker", StringComparison.OrdinalIgnoreCase) || 
                                     typeStr.Contains("SemanticRanker"))
                            {
                                semanticRankerActivities++;
                                _logger.LogDebug("🧮 Found semantic ranker activity");
                                
                                if (activityItem.TryGetProperty("inputTokens", out var semanticTokens))
                                {
                                    _logger.LogDebug("🎯 Semantic ranker tokens: {Tokens}", semanticTokens.GetInt32());
                                }
                            }
                        }
                    }
                    
                    // Assign SubQueries to response object (this was missing!)
                    response.SubQueries = subQueries;
                    
                    // Create detailed activity summary
                    var activityParts = new List<string>();
                    if (planningActivities > 0) activityParts.Add($"AI planning: {planningActivities}");
                    if (searchActivities > 0) activityParts.Add($"Search operations: {searchActivities}");
                    if (semanticRankerActivities > 0) activityParts.Add($"Semantic ranking: {semanticRankerActivities}");
                    
                    response.ActivityInfo = $"{string.Join(", ", activityParts)}, Total steps: {totalActivities}";
                    
                    _logger.LogInformation("✅ SubQueries extraction completed: {Count} sub-queries found", subQueries.Count);
                    foreach (var sq in subQueries)
                    {
                        _logger.LogInformation("📝 Sub-query: '{Query}' -> {ResultCount} results in {ElapsedMs}ms", 
                            sq.Query, sq.ResultCount, sq.ElapsedMs);
                    }
                }
                else
                {
                    _logger.LogWarning("⚠️ No activity array found in response");
                }
                
                // Extract references information following Microsoft's format
                if (root.TryGetProperty("references", out var references) && references.ValueKind == JsonValueKind.Array)
                {
                    var docRefs = 0;
                    var totalRefs = references.GetArrayLength();
                    
                    _logger.LogInformation("📚 Processing {Count} reference items", totalRefs);
                    
                    foreach (var reference in references.EnumerateArray())
                    {
                        if (reference.TryGetProperty("type", out var type))
                        {
                            var typeStr = type.GetString() ?? "";
                            if (typeStr.Equals("AzureSearchDoc", StringComparison.OrdinalIgnoreCase) || 
                                typeStr.Contains("Document")) 
                            {
                                docRefs++;
                            }
                        }
                    }
                    
                    response.ReferencesInfo = $"Referenced {docRefs} document(s) from knowledge base, Total sources: {totalRefs}";
                    _logger.LogInformation("📖 References summary: {Info}", response.ReferencesInfo);
                }
                else
                {
                    _logger.LogWarning("⚠️ No references array found in response");
                }
                
                _logger.LogInformation("🎯 ExtractActivityAndReferences completed successfully");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "❌ Error extracting activity and references");
                // Ensure we don't leave SubQueries null
                response.SubQueries ??= new List<SubQueryResult>();
            }
        }

        private string ExtractAnyText(string rawResponse)
        {
            try
            {
                // Try to find any readable text in the response
                var textMatches = Regex.Matches(rawResponse, @"""text""\s*:\s*""([^""]+)""", RegexOptions.IgnoreCase);
                if (textMatches.Count > 0)
                {
                    return textMatches[0].Groups[1].Value;
                }
                
                // Look for content fields
                var contentMatches = Regex.Matches(rawResponse, @"""content""\s*:\s*""([^""]+)""", RegexOptions.IgnoreCase);
                if (contentMatches.Count > 0)
                {
                    return contentMatches[0].Groups[1].Value;
                }
                
                // Fallback: return truncated raw response
                return rawResponse.Length > 500 ? rawResponse.Substring(0, 500) + "..." : rawResponse;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error extracting any text");
                return "Unable to parse response content.";
            }
        }

        public async Task<string> AgenticRetrieveAsync(string userQuery, string? systemPrompt = null)
        {
            try
            {
                _logger.LogInformation("Starting agentic retrieval for query: {Query}", userQuery);

                // Ensure knowledge agent exists
                await CheckKnowledgeAgentAsync();

                // Build system prompt for retail product recommendations
                var finalSystemPrompt = systemPrompt ?? @"
                I am a professional retail product consultant with comprehensive access to our product database. 
                My role is to provide personalized product recommendations based on customer needs, preferences, and budget constraints.

                My approach includes:
                1. Understanding specific customer needs and requirements
                2. Recommending 2-3 most suitable products with clear rationale
                3. Providing detailed product information including pricing and value analysis
                4. Asking clarifying questions when needed
                5. Suggesting alternatives when exact matches aren't available
                6. For price-related queries, I carefully filter products within the specified budget range

                I specialize in handling price range queries such as 'under $50', 'below $100', 'between $20-$100', 'less than $50', etc. 
                I understand various price expressions and will find products that match the budget criteria.

                I'm here to help you make informed purchasing decisions.
                ";

                // Create the retrieval request following Microsoft's agentic retrieval format
                // Note: Azure AI Search agentic API only supports 'user' and 'assistant' roles
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
                                    text = $"{finalSystemPrompt}\n\nUser Query: {userQuery}"
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
                            rerankerThreshold = 1.5,  // Lower threshold for better recall
                            maxDocsForReranker = 300   // More candidates for complex queries
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

                _logger.LogInformation("Executing agentic retrieval request");
                
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
                _logger.LogError(ex, "Error in agentic retrieval for query: {Query}", userQuery);
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
