using System.Text.Json;
using System.Text.RegularExpressions;
using retail_rag_web_app.Models;

namespace retail_rag_web_app.Services
{
    public class ResponseFormatterService
    {
        private readonly ILogger<ResponseFormatterService> _logger;

        public ResponseFormatterService(ILogger<ResponseFormatterService> logger)
        {
            _logger = logger;
        }

        public FormattedSearchResponse FormatRagResponse(string rawResponse, string query, int processingTimeMs = 0)
        {
            try
            {
                var formattedResponse = new FormattedSearchResponse
                {
                    Success = true,
                    SearchType = "RAG Search",
                    Query = query,
                    Metadata = new SearchMetadata
                    {
                        ProcessingTimeMs = processingTimeMs,
                        SearchStrategy = "Semantic Vector Search with RAG"
                    }
                };

                // Parse and format the RAG response
                var (summary, products, insights) = ParseRagContent(rawResponse);
                
                formattedResponse.Result = new FormattedResult
                {
                    Summary = summary,
                    Products = products,
                    Insights = insights,
                    Explanation = GenerateExplanation("RAG", query, products.Count)
                };

                formattedResponse.Metadata.TotalResults = products.Count;

                return formattedResponse;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error formatting RAG response");
                return new FormattedSearchResponse
                {
                    Success = false,
                    Error = "Failed to format response",
                    SearchType = "RAG Search",
                    Query = query
                };
            }
        }

        public FormattedSearchResponse FormatAgenticResponse(string rawResponse, string query, int processingTimeMs = 0)
        {
            try
            {
                var formattedResponse = new FormattedSearchResponse
                {
                    Success = true,
                    SearchType = "Agentic AI Search",
                    Query = query,
                    Metadata = new SearchMetadata
                    {
                        ProcessingTimeMs = processingTimeMs,
                        SearchStrategy = "AI-Powered Query Planning with Parallel Retrieval"
                    }
                };

                // Parse the agentic response JSON
                var agenticData = ParseAgenticJson(rawResponse);
                
                // Extract structured information
                var (summary, products, insights, recommendations) = ParseAgenticContent(agenticData);
                var subQueries = ExtractSubQueries(agenticData);
                var tokenUsage = ExtractTokenUsage(agenticData);
                var sources = ExtractSources(agenticData);

                formattedResponse.Result = new FormattedResult
                {
                    Summary = summary,
                    Products = products,
                    Insights = insights,
                    Recommendations = recommendations,
                    Explanation = GenerateExplanation("Agentic", query, products.Count)
                };

                formattedResponse.Metadata.SubQueries = subQueries;
                formattedResponse.Metadata.TokenUsage = tokenUsage;
                formattedResponse.Metadata.Sources = sources;
                formattedResponse.Metadata.TotalResults = products.Count;
                formattedResponse.Metadata.Stats = new SearchStats
                {
                    PlanningOperations = agenticData?.GetProperty("activity").EnumerateArray()
                        .Count(a => a.GetProperty("type").GetString()?.Contains("Planning") == true) ?? 0,
                    ParallelQueries = subQueries.Count,
                    DocumentsSearched = sources.Count
                };

                return formattedResponse;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error formatting Agentic response");
                return new FormattedSearchResponse
                {
                    Success = false,
                    Error = "Failed to format response",
                    SearchType = "Agentic AI Search",
                    Query = query
                };
            }
        }

        public FormattedSearchResponse FormatDataverseResponse(object rawResponse, string query, int processingTimeMs = 0)
        {
            try
            {
                var formattedResponse = new FormattedSearchResponse
                {
                    Success = true,
                    SearchType = "Dataverse Search",
                    Query = query,
                    Metadata = new SearchMetadata
                    {
                        ProcessingTimeMs = processingTimeMs,
                        SearchStrategy = "Enterprise Data Search with Unified API"
                    }
                };

                // Parse and format the Dataverse response
                var (summary, products, insights) = ParseDataverseContent(rawResponse);
                
                formattedResponse.Result = new FormattedResult
                {
                    Summary = summary,
                    Products = products,
                    Insights = insights,
                    Explanation = GenerateExplanation("Dataverse", query, products.Count)
                };

                formattedResponse.Metadata.TotalResults = products.Count;

                return formattedResponse;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error formatting Dataverse response");
                return new FormattedSearchResponse
                {
                    Success = false,
                    Error = "Failed to format response",
                    SearchType = "Dataverse Search",
                    Query = query
                };
            }
        }

        private (string summary, List<ProductResult> products, List<InsightItem> insights) ParseRagContent(string content)
        {
            var products = new List<ProductResult>();
            var insights = new List<InsightItem>();
            var summary = "";

            try
            {
                // Try to extract product information using regex patterns
                var productMatches = ExtractProductsFromText(content);
                products.AddRange(productMatches);

                // Extract insights and tips
                insights.AddRange(ExtractInsightsFromText(content));

                // Generate a clean summary
                summary = GenerateCleanSummary(content);
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error parsing RAG content, falling back to plain text");
                summary = CleanTextContent(content);
            }

            return (summary, products, insights);
        }

        private (string summary, List<ProductResult> products, List<InsightItem> insights, List<RecommendationItem> recommendations) 
            ParseAgenticContent(JsonElement? agenticData)
        {
            var products = new List<ProductResult>();
            var insights = new List<InsightItem>();
            var recommendations = new List<RecommendationItem>();
            var summary = "";

            try
            {
                if (agenticData.HasValue)
                {
                    // Extract main response content
                    var responseContent = ExtractResponseContent(agenticData.Value);
                    
                    // Parse products from the response
                    products.AddRange(ExtractProductsFromText(responseContent));
                    
                    // Extract insights
                    insights.AddRange(ExtractInsightsFromText(responseContent));
                    
                    // Generate recommendations based on AI reasoning
                    recommendations.AddRange(GenerateRecommendations(responseContent));
                    
                    // Clean summary
                    summary = GenerateAgenticSummary(products, responseContent);
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error parsing Agentic content");
            }

            return (summary, products, insights, recommendations);
        }

        private (string summary, List<ProductResult> products, List<InsightItem> insights) ParseDataverseContent(object rawContent)
        {
            var products = new List<ProductResult>();
            var insights = new List<InsightItem>();
            var summary = "";

            try
            {
                var jsonString = JsonSerializer.Serialize(rawContent);
                var jsonData = JsonSerializer.Deserialize<JsonElement>(jsonString);

                // Extract Dataverse-specific product information
                if (jsonData.TryGetProperty("value", out var valueArray) && valueArray.ValueKind == JsonValueKind.Array)
                {
                    foreach (var item in valueArray.EnumerateArray())
                    {
                        var product = ParseDataverseProduct(item);
                        if (product != null)
                            products.Add(product);
                    }
                }

                // Generate summary based on Dataverse results
                summary = GenerateDataverseSummary(products, jsonData);
                
                // Add Dataverse-specific insights
                insights.Add(new InsightItem
                {
                    Type = "info",
                    Title = "Enterprise Data",
                    Content = $"Retrieved {products.Count} products from enterprise database",
                    Icon = "fa-database",
                    Color = "info"
                });
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error parsing Dataverse content");
                summary = CleanTextContent(rawContent?.ToString() ?? "");
            }

            return (summary, products, insights);
        }

        private List<ProductResult> ExtractProductsFromText(string content)
        {
            var products = new List<ProductResult>();

            try
            {
                // First try to parse as JSON array (agentic response format)
                if (content.TrimStart().StartsWith("["))
                {
                    products.AddRange(ExtractProductsFromJsonArray(content));
                }

                // If JSON parsing didn't work or found no products, try text parsing
                if (products.Count == 0)
                {
                    // Pattern for product information with prices
                    var productPattern = @"(?i)(?:\*\*|##|#)?(?:name|product|title):\s*(.+?)(?:\n|\r|\s{2,})(?:.*?)?(?:price|cost):\s*\$?(\d+(?:\.\d{2})?)"
                        .Replace(@"\n", Environment.NewLine);

                    var matches = Regex.Matches(content, productPattern, RegexOptions.IgnoreCase | RegexOptions.Multiline);

                    foreach (Match match in matches)
                    {
                        if (match.Groups.Count >= 3)
                        {
                            var name = CleanProductName(match.Groups[1].Value);
                            if (decimal.TryParse(match.Groups[2].Value, out var price))
                            {
                                products.Add(new ProductResult
                                {
                                    Name = name,
                                    Price = price,
                                    Description = ExtractProductDescription(content, name),
                                    RelevanceScore = 0.8
                                });
                            }
                        }
                    }

                    // If no structured products found, try to extract from bullet points or numbered lists
                    if (products.Count == 0)
                    {
                        products.AddRange(ExtractProductsFromLists(content));
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error extracting products from text");
            }

            return products;
        }

        private List<ProductResult> ExtractProductsFromJsonArray(string jsonContent)
        {
            var products = new List<ProductResult>();

            try
            {
                var jsonArray = JsonSerializer.Deserialize<JsonElement[]>(jsonContent);
                
                if (jsonArray != null)
                {
                    foreach (var item in jsonArray)
                    {
                        if (item.TryGetProperty("content", out var contentElement))
                        {
                            var contentText = contentElement.GetString();
                            if (!string.IsNullOrEmpty(contentText))
                            {
                                var product = ParseProductFromAgenticContent(contentText);
                                if (product != null)
                                    products.Add(product);
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error parsing products from JSON array: {Error}", ex.Message);
            }

            return products;
        }

        private ProductResult? ParseProductFromAgenticContent(string content)
        {
            try
            {
                // Parse format like: "ProductNumber: 67104; Price: 45.0; Name: Conerics gloves; ItemId: 67104; Description: ..."
                var productNumber = ExtractValue(content, "ProductNumber");
                var priceStr = ExtractValue(content, "Price");
                var name = ExtractValue(content, "Name");
                var description = ExtractValue(content, "Description");

                if (!string.IsNullOrEmpty(name) && decimal.TryParse(priceStr, out var price))
                {
                    return new ProductResult
                    {
                        Name = name,
                        ProductNumber = productNumber,
                        Price = price,
                        Description = description,
                        RelevanceScore = 0.9
                    };
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error parsing product from agentic content");
            }

            return null;
        }

        private string ExtractValue(string content, string key)
        {
            var pattern = $@"{key}:\s*([^;]+)(?:;|$)";
            var match = Regex.Match(content, pattern, RegexOptions.IgnoreCase);
            return match.Success ? match.Groups[1].Value.Trim() : "";
        }

        private List<ProductResult> ExtractProductsFromLists(string content)
        {
            var products = new List<ProductResult>();
            
            // Pattern for list items that might contain products
            var listPattern = @"(?:^|\n)\s*(?:[-*•]|\d+\.)\s*(.+?)(?=\n|$)";
            var matches = Regex.Matches(content, listPattern, RegexOptions.Multiline);

            foreach (Match match in matches)
            {
                var item = match.Groups[1].Value.Trim();
                var product = ParseListItemAsProduct(item);
                if (product != null)
                    products.Add(product);
            }

            return products;
        }

        private ProductResult? ParseListItemAsProduct(string item)
        {
            // Look for price patterns in the item
            var pricePattern = @"\$(\d+(?:\.\d{2})?)";
            var priceMatch = Regex.Match(item, pricePattern);

            if (priceMatch.Success && decimal.TryParse(priceMatch.Groups[1].Value, out var price))
            {
                var name = item.Replace(priceMatch.Value, "").Trim(' ', '-', '*', '•');
                name = Regex.Replace(name, @"^\d+\.\s*", ""); // Remove numbering

                return new ProductResult
                {
                    Name = CleanProductName(name),
                    Price = price,
                    Description = ExtractFeatures(item),
                    RelevanceScore = 0.7
                };
            }

            return null;
        }

        private List<InsightItem> ExtractInsightsFromText(string content)
        {
            var insights = new List<InsightItem>();

            // Look for tips, warnings, or important information
            var tipPatterns = new[]
            {
                (@"(?i)(tip|advice|recommendation):\s*(.+?)(?=\n|$)", "tip", "fa-lightbulb", "success"),
                (@"(?i)(note|important|remember):\s*(.+?)(?=\n|$)", "info", "fa-info-circle", "info"),
                (@"(?i)(warning|caution|be aware):\s*(.+?)(?=\n|$)", "warning", "fa-exclamation-triangle", "warning"),
                (@"(?i)(comparison|vs|versus):\s*(.+?)(?=\n|$)", "comparison", "fa-balance-scale", "primary")
            };

            foreach (var (pattern, type, icon, color) in tipPatterns)
            {
                var matches = Regex.Matches(content, pattern);
                foreach (Match match in matches)
                {
                    if (match.Groups.Count >= 3)
                    {
                        insights.Add(new InsightItem
                        {
                            Type = type,
                            Title = match.Groups[1].Value,
                            Content = match.Groups[2].Value.Trim(),
                            Icon = icon,
                            Color = color
                        });
                    }
                }
            }

            return insights;
        }

        private List<RecommendationItem> GenerateRecommendations(string content)
        {
            var recommendations = new List<RecommendationItem>();

            // Analyze content for recommendation patterns
            if (content.ToLower().Contains("budget") || content.ToLower().Contains("under $"))
            {
                recommendations.Add(new RecommendationItem
                {
                    Title = "Budget-Friendly Options",
                    Description = "Consider these cost-effective alternatives that provide great value",
                    Icon = "fa-dollar-sign",
                    Category = "Budget",
                    Tags = new List<string> { "affordable", "value", "savings" }
                });
            }

            if (content.ToLower().Contains("feature") || content.ToLower().Contains("quality"))
            {
                recommendations.Add(new RecommendationItem
                {
                    Title = "Feature Comparison",
                    Description = "Compare key features to find the best fit for your needs",
                    Icon = "fa-list-check",
                    Category = "Features",
                    Tags = new List<string> { "comparison", "features", "analysis" }
                });
            }

            return recommendations;
        }

        private JsonElement? ParseAgenticJson(string rawResponse)
        {
            try
            {
                return JsonSerializer.Deserialize<JsonElement>(rawResponse);
            }
            catch
            {
                _logger.LogWarning("Failed to parse agentic response as JSON");
                return null;
            }
        }

        private string ExtractResponseContent(JsonElement agenticData)
        {
            try
            {
                // Try different possible paths for the response content
                if (agenticData.TryGetProperty("response", out var response) && response.ValueKind == JsonValueKind.Array)
                {
                    foreach (var item in response.EnumerateArray())
                    {
                        if (item.TryGetProperty("role", out var role) && role.GetString() == "assistant")
                        {
                            if (item.TryGetProperty("content", out var content) && content.ValueKind == JsonValueKind.Array)
                            {
                                foreach (var contentItem in content.EnumerateArray())
                                {
                                    if (contentItem.TryGetProperty("text", out var text))
                                    {
                                        return text.GetString() ?? "";
                                    }
                                }
                            }
                        }
                    }
                }

                // Fallback to raw JSON string representation
                return agenticData.GetRawText();
            }
            catch
            {
                return "";
            }
        }

        private List<SubQueryDetail> ExtractSubQueries(JsonElement? agenticData)
        {
            var subQueries = new List<SubQueryDetail>();

            if (!agenticData.HasValue) return subQueries;

            try
            {
                if (agenticData.Value.TryGetProperty("activity", out var activity) && activity.ValueKind == JsonValueKind.Array)
                {
                    int index = 1;
                    foreach (var item in activity.EnumerateArray())
                    {
                        if (item.TryGetProperty("type", out var type) && 
                            type.GetString()?.Contains("Search") == true)
                        {
                            var subQuery = new SubQueryDetail
                            {
                                Index = index++,
                                ElapsedMs = item.TryGetProperty("elapsedMs", out var elapsed) ? elapsed.GetInt32() : 0,
                                ResultCount = item.TryGetProperty("count", out var count) ? count.GetInt32() : 0
                            };

                            if (item.TryGetProperty("query", out var queryObj))
                            {
                                if (queryObj.TryGetProperty("search", out var search))
                                {
                                    subQuery.Query = search.GetString() ?? "";
                                }
                                if (queryObj.TryGetProperty("filter", out var filter))
                                {
                                    subQuery.Filter = filter.GetString();
                                }
                            }

                            subQuery.Purpose = GenerateQueryPurpose(subQuery.Query);
                            subQueries.Add(subQuery);
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error extracting sub-queries");
            }

            return subQueries;
        }

        private TokenUsage ExtractTokenUsage(JsonElement? agenticData)
        {
            if (!agenticData.HasValue) return new TokenUsage();

            try
            {
                var tokenUsage = new TokenUsage();
                
                if (agenticData.Value.TryGetProperty("activity", out var activity) && activity.ValueKind == JsonValueKind.Array)
                {
                    foreach (var item in activity.EnumerateArray())
                    {
                        if (item.TryGetProperty("inputTokens", out var inputTokens))
                        {
                            tokenUsage.InputTokens += inputTokens.GetInt32();
                        }
                        if (item.TryGetProperty("outputTokens", out var outputTokens))
                        {
                            tokenUsage.OutputTokens += outputTokens.GetInt32();
                        }
                    }
                }

                // Rough cost estimation (adjust based on actual pricing)
                tokenUsage.EstimatedCost = (tokenUsage.TotalTokens * 0.00002m); // ~$0.02 per 1K tokens

                return tokenUsage;
            }
            catch
            {
                return new TokenUsage();
            }
        }

        private List<SourceReference> ExtractSources(JsonElement? agenticData)
        {
            var sources = new List<SourceReference>();

            if (!agenticData.HasValue) return sources;

            try
            {
                if (agenticData.Value.TryGetProperty("references", out var references) && references.ValueKind == JsonValueKind.Array)
                {
                    foreach (var item in references.EnumerateArray())
                    {
                        var source = new SourceReference();
                        
                        if (item.TryGetProperty("id", out var id))
                            source.Id = id.GetString() ?? "";
                        
                        if (item.TryGetProperty("docKey", out var docKey))
                            source.Title = docKey.GetString() ?? "";

                        if (item.TryGetProperty("sourceData", out var sourceData))
                        {
                            if (sourceData.TryGetProperty("title", out var title))
                                source.Title = title.GetString() ?? source.Title;
                            
                            if (sourceData.TryGetProperty("content", out var content))
                                source.Content = content.GetString() ?? "";
                        }

                        source.RelevanceScore = 0.8; // Default relevance
                        sources.Add(source);
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error extracting sources");
            }

            return sources;
        }

        private ProductResult? ParseDataverseProduct(JsonElement item)
        {
            try
            {
                var product = new ProductResult();
                
                // Map Dataverse fields to product properties
                if (item.TryGetProperty("name", out var name))
                    product.Name = name.GetString() ?? "";
                
                if (item.TryGetProperty("price", out var price) && price.TryGetDecimal(out var priceValue))
                    product.Price = priceValue;
                
                if (item.TryGetProperty("productnumber", out var productNumber))
                    product.ProductNumber = productNumber.GetString() ?? "";
                
                if (item.TryGetProperty("description", out var description))
                    product.Description = description.GetString() ?? "";

                // Set default relevance score
                product.RelevanceScore = 0.9;

                return string.IsNullOrEmpty(product.Name) ? null : product;
            }
            catch
            {
                return null;
            }
        }

        private string GenerateCleanSummary(string content)
        {
            // Clean and format the content for display
            var summary = CleanTextContent(content);
            
            // Truncate if too long
            if (summary.Length > 500)
            {
                summary = summary.Substring(0, 497) + "...";
            }

            return summary;
        }

        private string GenerateAgenticSummary(List<ProductResult> products, string rawContent)
        {
            try
            {
                if (products.Count == 0)
                {
                    return "AI agent searched for products but found no exact matches. Try adjusting your search terms or price range.";
                }

                var productNames = products.Take(3).Select(p => p.Name).ToList();
                var priceRange = products.Count > 1 
                    ? $"${products.Min(p => p.Price):F2} - ${products.Max(p => p.Price):F2}"
                    : $"${products.First().Price:F2}";

                var summary = $"Found {products.Count} product{(products.Count > 1 ? "s" : "")} matching your criteria. ";
                
                if (products.Count == 1)
                {
                    summary += $"The product is **{productNames.First()}** priced at {priceRange}.";
                }
                else if (products.Count <= 3)
                {
                    summary += $"Products include: **{string.Join("**, **", productNames)}** with prices ranging from {priceRange}.";
                }
                else
                {
                    summary += $"Top products include: **{string.Join("**, **", productNames)}** and {products.Count - 3} more, with prices ranging from {priceRange}.";
                }

                return summary;
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error generating agentic summary");
                return GenerateCleanSummary(rawContent);
            }
        }

        private string CleanTextContent(string content)
        {
            if (string.IsNullOrEmpty(content)) return "";

            // Remove excessive whitespace and clean up formatting
            content = Regex.Replace(content, @"\s+", " ");
            content = Regex.Replace(content, @"\n\s*\n", "\n\n");
            content = content.Trim();

            return content;
        }

        private string CleanProductName(string name)
        {
            // Clean up product names by removing common prefixes/suffixes
            name = Regex.Replace(name, @"^\d+\.\s*", ""); // Remove numbering
            name = Regex.Replace(name, @"^[-*•]\s*", ""); // Remove bullet points
            name = name.Trim();
            
            return name;
        }

        private string ExtractProductDescription(string content, string productName)
        {
            // Try to find description near the product name
            var productIndex = content.IndexOf(productName, StringComparison.OrdinalIgnoreCase);
            if (productIndex >= 0)
            {
                var start = Math.Max(0, productIndex - 100);
                var end = Math.Min(content.Length, productIndex + productName.Length + 200);
                var context = content.Substring(start, end - start);
                
                // Extract meaningful description
                var sentences = context.Split('.', StringSplitOptions.RemoveEmptyEntries);
                return sentences.Length > 1 ? sentences[1].Trim() : context.Trim();
            }
            
            return "";
        }

        private string ExtractFeatures(string item)
        {
            // Extract feature keywords from product descriptions
            var features = new List<string>();
            var keywords = new[] { "wireless", "bluetooth", "waterproof", "rechargeable", "portable", "durable", "lightweight" };
            
            foreach (var keyword in keywords)
            {
                if (item.ToLower().Contains(keyword))
                    features.Add(keyword);
            }
            
            return string.Join(", ", features);
        }

        private string GenerateQueryPurpose(string query)
        {
            // Generate human-readable purpose for sub-queries
            if (string.IsNullOrEmpty(query)) return "General search";
            
            if (query.ToLower().Contains("price"))
                return "Price analysis";
            if (query.ToLower().Contains("feature"))
                return "Feature comparison";
            if (query.ToLower().Contains("review"))
                return "Review analysis";
            if (query.ToLower().Contains("spec"))
                return "Specification lookup";
            
            return "Product discovery";
        }

        private string GenerateDataverseSummary(List<ProductResult> products, JsonElement jsonData)
        {
            if (products.Count == 0)
                return "No products found in the enterprise database.";
            
            var categories = products.Select(p => ExtractCategory(p.Name)).Distinct().ToList();
            var avgPrice = products.Where(p => p.Price > 0).Select(p => p.Price).DefaultIfEmpty(0).Average();
            
            return $"Found {products.Count} products across {categories.Count} categories. " +
                   $"Average price: ${avgPrice:F2}. Data retrieved from enterprise Dataverse.";
        }

        private string ExtractCategory(string productName)
        {
            // Simple category extraction based on product name
            var categoryKeywords = new Dictionary<string, string>
            {
                { "laptop", "Electronics" },
                { "phone", "Electronics" },
                { "book", "Books" },
                { "clothing", "Apparel" },
                { "shoe", "Footwear" },
                { "kitchen", "Home & Kitchen" },
                { "toy", "Toys & Games" }
            };

            foreach (var (keyword, category) in categoryKeywords)
            {
                if (productName.ToLower().Contains(keyword))
                    return category;
            }

            return "General";
        }

        private string GenerateExplanation(string searchType, string query, int resultCount)
        {
            return searchType switch
            {
                "RAG" => $"Used semantic vector search to find {resultCount} relevant products for '{query}'. " +
                        "Results are ranked by semantic similarity to your query.",
                
                "Agentic" => $"AI agent analyzed your query '{query}' and created optimized sub-queries to find {resultCount} products. " +
                           "The agent used intelligent query planning and parallel search for comprehensive results.",
                
                "Dataverse" => $"Searched enterprise database for '{query}' and found {resultCount} products. " +
                              "Results include complete product information from our business systems.",
                
                _ => $"Found {resultCount} results for your query '{query}'."
            };
        }
    }
}
