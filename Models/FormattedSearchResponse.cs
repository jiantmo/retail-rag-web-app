using System.Text.Json.Serialization;

namespace retail_rag_web_app.Models
{
    public class FormattedSearchResponse
    {
        public bool Success { get; set; } = true;
        public string SearchType { get; set; } = string.Empty;
        public string Query { get; set; } = string.Empty;
        public FormattedResult Result { get; set; } = new();
        public SearchMetadata Metadata { get; set; } = new();
        public string? Error { get; set; }
    }

    public class FormattedResult
    {
        public string Summary { get; set; } = string.Empty;
        public List<ProductResult> Products { get; set; } = new();
        public List<RecommendationItem> Recommendations { get; set; } = new();
        public List<InsightItem> Insights { get; set; } = new();
        public string Explanation { get; set; } = string.Empty;
    }

    public class RecommendationItem
    {
        public string Title { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string Icon { get; set; } = "fa-lightbulb";
        public string Category { get; set; } = string.Empty;
        public List<string> Tags { get; set; } = new();
    }

    public class InsightItem
    {
        public string Type { get; set; } = string.Empty; // "tip", "warning", "info", "comparison"
        public string Title { get; set; } = string.Empty;
        public string Content { get; set; } = string.Empty;
        public string Icon { get; set; } = "fa-info-circle";
        public string Color { get; set; } = "info";
    }

    public class SearchMetadata
    {
        public DateTime Timestamp { get; set; } = DateTime.UtcNow;
        public int ProcessingTimeMs { get; set; }
        public int TotalResults { get; set; }
        public List<SubQueryDetail> SubQueries { get; set; } = new();
        public TokenUsage TokenUsage { get; set; } = new();
        public List<SourceReference> Sources { get; set; } = new();
        public SearchStats Stats { get; set; } = new();
        public string SearchStrategy { get; set; } = string.Empty;
    }

    public class SubQueryDetail
    {
        public int Index { get; set; }
        public string Query { get; set; } = string.Empty;
        public string? Filter { get; set; }
        public int ResultCount { get; set; }
        public int ElapsedMs { get; set; }
        public DateTime QueryTime { get; set; }
        public string Purpose { get; set; } = string.Empty; // Human-readable explanation
    }

    public class TokenUsage
    {
        public int InputTokens { get; set; }
        public int OutputTokens { get; set; }
        public int TotalTokens => InputTokens + OutputTokens;
        public decimal EstimatedCost { get; set; } // In USD
    }

    public class SourceReference
    {
        public string Id { get; set; } = string.Empty;
        public string Title { get; set; } = string.Empty;
        public string Type { get; set; } = "document";
        public string Content { get; set; } = string.Empty;
        public double RelevanceScore { get; set; }
    }

    public class SearchStats
    {
        public int DocumentsSearched { get; set; }
        public int DocumentsRanked { get; set; }
        public int PlanningOperations { get; set; }
        public int ParallelQueries { get; set; }
    }

    // Enhanced ProductResult with better formatting
    public class EnhancedProductResult : ProductResult
    {
        public List<ProductFeature> Features { get; set; } = new();
        public ProductRating Rating { get; set; } = new();
        public List<ProductVariant> Variants { get; set; } = new();
        public ProductAvailability Availability { get; set; } = new();
        public string Category { get; set; } = string.Empty;
        public string Subcategory { get; set; } = string.Empty;
        public List<string> Tags { get; set; } = new();
        public string Brand { get; set; } = string.Empty;
        public DateTime? ReleaseDate { get; set; }
        public string SEOUrl { get; set; } = string.Empty;
        public string WhyRecommended { get; set; } = string.Empty;
    }

    public class ProductFeature
    {
        public string Name { get; set; } = string.Empty;
        public string Value { get; set; } = string.Empty;
        public string Icon { get; set; } = "fa-check";
        public bool IsHighlight { get; set; } = false;
    }

    public class ProductRating
    {
        public double Score { get; set; } = 0.0;
        public int ReviewCount { get; set; } = 0;
        public List<RatingDistribution> Distribution { get; set; } = new();
    }

    public class RatingDistribution
    {
        public int Stars { get; set; }
        public int Count { get; set; }
        public double Percentage { get; set; }
    }

    public class ProductVariant
    {
        public string Type { get; set; } = string.Empty; // "color", "size", "model"
        public string Value { get; set; } = string.Empty;
        public decimal PriceAdjustment { get; set; } = 0;
        public bool IsAvailable { get; set; } = true;
        public string ImageUrl { get; set; } = string.Empty;
    }

    public class ProductAvailability
    {
        public bool InStock { get; set; } = true;
        public int Quantity { get; set; } = 0;
        public string Status { get; set; } = "In Stock";
        public DateTime? EstimatedRestock { get; set; }
        public List<string> AvailableLocations { get; set; } = new();
    }
}
