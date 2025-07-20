using Microsoft.AspNetCore.Mvc;
using retail_rag_web_app.Models;
using retail_rag_web_app.Services;
using System.Threading.Tasks;

namespace retail_rag_web_app.Controllers
{
    [Route("search")]
    public class SearchController : Controller
    {
        private readonly RagService _ragService;
        private readonly ILogger<SearchController> _logger;

        public SearchController(RagService ragService, ILogger<SearchController> logger)
        {
            _ragService = ragService;
            _logger = logger;
        }

        [HttpGet]
        public IActionResult Index()
        {
            return View();
        }

        [HttpGet("image")]
        public IActionResult ImageSearch()
        {
            return View();
        }

        [HttpGet("test")]
        public IActionResult Test()
        {
            return View();
        }

        [HttpGet("simple")]
        public IActionResult Simple()
        {
            return View();
        }

        [HttpPost("execute")]
        public async Task<IActionResult> ExecuteSearch([FromBody] SearchRequest searchRequest)
        {
            try
            {
                // Log the raw request body for debugging
                Request.EnableBuffering();
                var body = await new StreamReader(Request.Body).ReadToEndAsync();
                Request.Body.Position = 0;
                _logger.LogInformation("Raw request body: {Body}", body);
                
                _logger.LogInformation("Received search request. SearchRequest is null: {IsNull}", searchRequest == null);
                
                if (searchRequest == null)
                {
                    _logger.LogWarning("SearchRequest object is null");
                    return BadRequest("SearchRequest object is null.");
                }
                
                _logger.LogInformation("SearchRequest Query: '{Query}', IsEmpty: {IsEmpty}", 
                    searchRequest.Query, string.IsNullOrWhiteSpace(searchRequest.Query));
                
                if (string.IsNullOrWhiteSpace(searchRequest.Query))
                {
                    _logger.LogWarning("Query is null or empty");
                    return BadRequest("Query is required.");
                }

                _logger.LogInformation("Processing search query: {Query}", searchRequest.Query);

                var result = await _ragService.SearchAsync(searchRequest.Query);
                return Json(new { success = true, result });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing search request: {Error}", ex.Message);
                return Json(new { success = false, error = "An error occurred while processing your request." });
            }
        }

        [HttpPost("stream")]
        public async Task<IActionResult> StreamSearch([FromBody] SearchRequest searchRequest)
        {
            try
            {
                if (searchRequest == null || string.IsNullOrWhiteSpace(searchRequest.Query))
                {
                    return BadRequest("Invalid search request.");
                }

                _logger.LogInformation("Processing streaming search query: {Query}", searchRequest.Query);

                // 设置SSE响应头 - 兼容HTTP/2
                Response.ContentType = "text/event-stream";
                Response.Headers["Cache-Control"] = "no-cache";
                Response.Headers["X-Accel-Buffering"] = "no";

                // 开始流式响应
                await foreach (var chunk in _ragService.SearchStreamRealTimeAsync(searchRequest.Query))
                {
                    await WriteSSEAsync("message", new { text = chunk });
                    await Task.Delay(50);
                }

                // 发送结束标志
                await WriteSSEAsync("message", new { completed = true });

                return new EmptyResult();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing streaming search request: {Error}", ex.Message);
                await WriteSSEAsync("message", new { error = ex.Message });
                return new EmptyResult();
            }
        }

        private async Task WriteSSEAsync(string eventType, object data)
        {
            var jsonData = System.Text.Json.JsonSerializer.Serialize(data);
            await Response.WriteAsync($"event: {eventType}\n");
            await Response.WriteAsync($"data: {jsonData}\n");
            await Response.WriteAsync("\n");
            await Response.Body.FlushAsync();
        }
    }
}
