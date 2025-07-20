using System.ComponentModel.DataAnnotations;

namespace retail_rag_web_app.Models
{
    public class SearchRequest
    {
        public string Query { get; set; } = string.Empty;
        public string? Filter { get; set; }
        public bool UseStreaming { get; set; } = false;
        
        // Image search properties
        public string? ImageData { get; set; } // Base64 encoded image
        public string? ImageUrl { get; set; } // Image URL
        public bool IsImageSearch { get; set; } = false;
        public SearchMode SearchMode { get; set; } = SearchMode.Text;
    }

    public enum SearchMode
    {
        Text,
        Image,
        Multimodal // Both text and image
    }
}