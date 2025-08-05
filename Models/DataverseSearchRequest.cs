using System.Text.Json.Serialization;

namespace retail_rag_web_app.Models
{
    public class DataverseSearchRequest
    {
        [JsonPropertyName("queryText")]
        public string QueryText { get; set; } = string.Empty;

        [JsonPropertyName("skill")]
        public string Skill { get; set; } = string.Empty;

        [JsonPropertyName("options")]
        public List<string> Options { get; set; } = new List<string> { "GetResultsSummary" };

        [JsonPropertyName("additionalProperties")]
        public Dictionary<string, object> AdditionalProperties { get; set; } = new Dictionary<string, object>
        {
            { "ExecuteUnifiedSearch", true }
        };

        [JsonPropertyName("bearerToken")]
        public string? BearerToken { get; set; }
    }

    public class DataverseSearchResponse
    {
        [JsonPropertyName("results")]
        public List<DataverseResult>? Results { get; set; }

        [JsonPropertyName("summary")]
        public string? Summary { get; set; }

        [JsonPropertyName("success")]
        public bool Success { get; set; }

        [JsonPropertyName("error")]
        public string? Error { get; set; }
        
        /// <summary>
        /// Raw API response from Dataverse for frontend processing
        /// </summary>
        [JsonPropertyName("rawApiResponse")]
        public string? RawApiResponse { get; set; }
    }

    public class DataverseResult
    {
        [JsonPropertyName("id")]
        public string? Id { get; set; }

        [JsonPropertyName("title")]
        public string? Title { get; set; }

        [JsonPropertyName("content")]
        public string? Content { get; set; }

        [JsonPropertyName("score")]
        public double Score { get; set; }
    }
}
