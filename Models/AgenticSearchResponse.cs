using System.Text.Json.Serialization;

namespace retail_rag_web_app.Models
{
    public class AgenticSearchResponse
    {
        public string Content { get; set; } = "";
        public AgenticSearchActivity[] Activity { get; set; } = Array.Empty<AgenticSearchActivity>();
        public AgenticSearchReference[] References { get; set; } = Array.Empty<AgenticSearchReference>();
        public string FinalPrompt { get; set; } = "";
        public bool Success { get; set; } = true;
        public string? Error { get; set; }
    }

    public class AgenticSearchActivity
    {
        public string Type { get; set; } = "";
        public int Id { get; set; }
        public string? TargetIndex { get; set; }
        public AgenticSearchQuery? Query { get; set; }
        public DateTime? QueryTime { get; set; }
        public int? Count { get; set; }
        public int? ElapsedMs { get; set; }
        public int? InputTokens { get; set; }
        public int? OutputTokens { get; set; }
    }

    public class AgenticSearchQuery
    {
        public string Search { get; set; } = "";
        public string? Filter { get; set; }
    }

    public class AgenticSearchReference
    {
        public string Type { get; set; } = "";
        public string Id { get; set; } = "";
        public int? ActivitySource { get; set; }
        public string DocKey { get; set; } = "";
        public AgenticSearchSourceData? SourceData { get; set; }
    }

    public class AgenticSearchSourceData
    {
        public string Id { get; set; } = "";
        public string Title { get; set; } = "";
        public string Content { get; set; } = "";
        public string Terms { get; set; } = "";
    }

    public class SubQueryResult
    {
        public string Query { get; set; } = "";
        public string? Filter { get; set; }
        public int ResultCount { get; set; }
        public int ElapsedMs { get; set; }
        public DateTime QueryTime { get; set; }
        public List<AgenticSearchReference> Results { get; set; } = new();
    }

    public class AgenticSearchDetails
    {
        public string OriginalQuery { get; set; } = "";
        public List<SubQueryResult> SubQueries { get; set; } = new();
        public string FinalContent { get; set; } = "";
        public string FinalPrompt { get; set; } = "";
        public int TotalInputTokens { get; set; }
        public int TotalOutputTokens { get; set; }
        public int TotalElapsedMs { get; set; }
        public List<AgenticSearchReference> AllReferences { get; set; } = new();
    }
}
