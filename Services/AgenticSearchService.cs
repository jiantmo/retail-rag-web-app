using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using retail_rag_web_app.Models;
using retail_rag_web_app.Services;
using System.Text.Json;

namespace retail_rag_web_app.Services
{
    public class AgenticSearchService
    {
        private readonly KnowledgeAgentManagementService _knowledgeAgentService;
        private readonly ILogger<AgenticSearchService> _logger;

        public AgenticSearchService(KnowledgeAgentManagementService knowledgeAgentService, ILogger<AgenticSearchService> logger)
        {
            _knowledgeAgentService = knowledgeAgentService;
            _logger = logger;
        }

        public async Task<AgenticSearchDetails> PerformAgenticSearchAsync(string query, string? assistantContext = null)
        {
            try
            {
                _logger.LogInformation("Starting agentic search for query: {Query}", query);

                // Perform the agentic retrieval
                var response = await _knowledgeAgentService.TestKnowledgeAgentAsync(query, null, "user", assistantContext);

                // Check for null response
                if (response == null)
                {
                    _logger.LogWarning("Received null response from knowledge agent");
                    return new AgenticSearchDetails
                    {
                        OriginalQuery = query,
                        FinalContent = "No response received from knowledge agent.",
                        AllReferences = new List<AgenticSearchReference>(),
                        SubQueries = new List<SubQueryResult>()
                    };
                }

                // Process the response to extract detailed information
                var details = ProcessAgenticResponse(query, response);

                _logger.LogInformation("Agentic search completed. Found {SubQueryCount} sub-queries", details.SubQueries.Count);

                return details;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error performing agentic search: {Error}", ex.Message);
                throw;
            }
        }

        private AgenticSearchDetails ProcessAgenticResponse(string originalQuery, AgenticRetrievalResponse response)
        {
            _logger.LogInformation($"Processing agentic response. Activity count: {response.Activity?.Length ?? 0}");
            
            var details = new AgenticSearchDetails
            {
                OriginalQuery = originalQuery,
                FinalContent = response.Content,
                AllReferences = response.References?.Select(r => new AgenticSearchReference
                {
                    Type = r.Type,
                    Id = r.Id,
                    ActivitySource = r.ActivitySource,
                    DocKey = r.DocKey,
                    SourceData = r.SourceData != null ? new AgenticSearchSourceData
                    {
                        Id = r.SourceData.Id,
                        Title = r.SourceData.Title,
                        Content = r.SourceData.Content,
                        Terms = r.SourceData.Terms
                    } : null
                }).ToList() ?? new List<AgenticSearchReference>()
            };

            // Process activities to extract sub-queries
            if (response.Activity != null)
            {
                _logger.LogInformation($"Found {response.Activity.Length} activities");
                var subQueries = new List<SubQueryResult>();
                var queryActivities = response.Activity.Where(a => a.Type == "AzureSearchQuery").ToList();
                _logger.LogInformation($"Found {queryActivities.Count} query activities");

                foreach (var activity in queryActivities)
                {
                    _logger.LogInformation($"Processing activity {activity.Id}, type: {activity.Type}, query: {activity.Query?.Search}");
                    if (activity.Query != null)
                    {
                        var subQuery = new SubQueryResult
                        {
                            Query = activity.Query.Search,
                            Filter = activity.Query.Filter,
                            ResultCount = activity.Count ?? 0,
                            ElapsedMs = activity.ElapsedMs ?? 0,
                            QueryTime = activity.QueryTime ?? DateTime.UtcNow,
                            Results = details.AllReferences
                                .Where(r => r.ActivitySource == activity.Id)
                                .ToList()
                        };
                        subQueries.Add(subQuery);
                    }
                }

                details.SubQueries = subQueries;

                // Calculate totals
                details.TotalInputTokens = response.Activity.Sum(a => a.InputTokens ?? 0);
                details.TotalOutputTokens = response.Activity.Sum(a => a.OutputTokens ?? 0);
                details.TotalElapsedMs = response.Activity.Sum(a => a.ElapsedMs ?? 0);
            }

            // Extract final prompt from response if available
            if (response.Response != null && response.Response.Length > 0)
            {
                var assistantMessage = response.Response.FirstOrDefault(r => r.Role == "assistant");
                if (assistantMessage?.Content != null && assistantMessage.Content.Length > 0)
                {
                    details.FinalPrompt = assistantMessage.Content.FirstOrDefault()?.Text ?? "";
                }
            }

            // If no final prompt in response, construct it from the content
            if (string.IsNullOrEmpty(details.FinalPrompt) && !string.IsNullOrEmpty(details.FinalContent))
            {
                details.FinalPrompt = ConstructFinalPrompt(originalQuery, details.FinalContent);
            }

            return details;
        }

        private string ConstructFinalPrompt(string query, string content)
        {
            return $@"Based on the following search results, please provide a comprehensive answer to the user's query.

User Query: {query}

Search Results:
{content}

Please provide a helpful, accurate response based on the above information. If the search results don't contain enough information to fully answer the query, please indicate what information is missing.";
        }

        public async Task<AgenticSearchResponse> PerformAgenticSearchWithResponseAsync(string query, string? assistantContext = null)
        {
            try
            {
                var details = await PerformAgenticSearchAsync(query, assistantContext);

                return new AgenticSearchResponse
                {
                    Content = details.FinalContent,
                    Activity = details.SubQueries.Select((sq, index) => new AgenticSearchActivity
                    {
                        Type = "AzureSearchQuery",
                        Id = index + 1,
                        Query = new AgenticSearchQuery
                        {
                            Search = sq.Query,
                            Filter = sq.Filter
                        },
                        QueryTime = sq.QueryTime,
                        Count = sq.ResultCount,
                        ElapsedMs = sq.ElapsedMs
                    }).ToArray(),
                    References = details.AllReferences.ToArray(),
                    FinalPrompt = details.FinalPrompt,
                    Success = true
                };
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in agentic search: {Error}", ex.Message);
                return new AgenticSearchResponse
                {
                    Success = false,
                    Error = ex.Message
                };
            }
        }
    }
}
