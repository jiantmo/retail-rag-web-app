using System.Text.Json.Serialization;

namespace retail_rag_web_app.Models
{
    public class ProductResult
    {
        public string Name { get; set; } = string.Empty;
        public decimal Price { get; set; }
        public string ProductNumber { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string Color { get; set; } = string.Empty;
        public string Size { get; set; } = string.Empty;
        public string Material { get; set; } = string.Empty;
        public List<string> ImageUrls { get; set; } = new List<string>();
        public string RefId { get; set; } = string.Empty;
        public double RelevanceScore { get; set; }
    }

    public class AgenticSearchFormattedResponse
    {
        public bool IsProductList { get; set; }
        public List<ProductResult> Products { get; set; } = new List<ProductResult>();
        public string FormattedText { get; set; } = string.Empty;
        public string ActivityInfo { get; set; } = string.Empty;
        public string ReferencesInfo { get; set; } = string.Empty;
        public string RawResponse { get; set; } = string.Empty;
    }
}
