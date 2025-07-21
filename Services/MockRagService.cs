using retail_rag_web_app.Models;

namespace retail_rag_web_app.Services
{
    public class MockRagService
    {
        private readonly ILogger<MockRagService> _logger;

        public MockRagService(ILogger<MockRagService> logger)
        {
            _logger = logger;
        }

        public async Task<object> SearchAsync(string query)
        {
            _logger.LogInformation("Mock RAG Search for query: {Query}", query);
            
            // 模拟异步操作
            await Task.Delay(1000);

            // 返回模拟的搜索结果
            return new
            {
                query = query,
                results = new[]
                {
                    new
                    {
                        title = "Product 1 - Perfect Gift for Kids",
                        description = "This is a perfect gift option for a 12-year-old daughter. Educational and fun!",
                        price = "$29.99",
                        rating = 4.5,
                        image = "https://via.placeholder.com/200x200?text=Product+1"
                    },
                    new
                    {
                        title = "Product 2 - Creative Art Set",
                        description = "Encourages creativity and artistic expression. Great for kids aged 10-15.",
                        price = "$39.99",
                        rating = 4.7,
                        image = "https://via.placeholder.com/200x200?text=Product+2"
                    },
                    new
                    {
                        title = "Product 3 - Science Discovery Kit",
                        description = "STEM learning made fun! Perfect for curious minds and young scientists.",
                        price = "$49.99",
                        rating = 4.8,
                        image = "https://via.placeholder.com/200x200?text=Product+3"
                    }
                },
                searchTime = "1.2 seconds",
                totalResults = 25
            };
        }
    }
}
