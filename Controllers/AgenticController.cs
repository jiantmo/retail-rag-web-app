using Microsoft.AspNetCore.Mvc;
using retail_rag_web_app.Services;
using retail_rag_web_app.Models;
using System.Diagnostics;

namespace retail_rag_web_app.Controllers
{
    [Route("agentic")]
    public class AgenticController : Controller
    {
        private readonly AgenticRetrievalService _agenticService;
        private readonly ResponseFormatterService _formatterService;
        private readonly ILogger<AgenticController> _logger;

        public AgenticController(
            AgenticRetrievalService agenticService, 
            ResponseFormatterService formatterService,
            ILogger<AgenticController> logger)
        {
            _agenticService = agenticService;
            _formatterService = formatterService;
            _logger = logger;
        }

        [HttpGet]
        public IActionResult Index()
        {
            return View();
        }

        [HttpPost("search")]
        public async Task<IActionResult> Search([FromBody] AgenticSearchRequest request)
        {
            var stopwatch = Stopwatch.StartNew();
            
            try
            {
                if (request == null || string.IsNullOrWhiteSpace(request.Query))
                {
                    return BadRequest(new FormattedSearchResponse
                    {
                        Success = false,
                        Error = "Invalid search request.",
                        SearchType = "Agentic AI Search",
                        Query = request?.Query ?? ""
                    });
                }

                _logger.LogInformation("Processing agentic search query: {Query}", request.Query);

                // Use the AgenticRetrieveAsync method to get raw response
                var rawResponseJson = await _agenticService.AgenticRetrieveAsync(request.Query, request.SystemPrompt);
                stopwatch.Stop();

                // Format the response using the formatter service
                var formattedResponse = _formatterService.FormatAgenticResponse(
                    rawResponseJson, 
                    request.Query, 
                    (int)stopwatch.ElapsedMilliseconds);

                return Json(formattedResponse);
            }
            catch (Exception ex)
            {
                stopwatch.Stop();
                _logger.LogError(ex, "Error processing agentic search request: {Error}", ex.Message);
                
                var errorResponse = new FormattedSearchResponse
                {
                    Success = false,
                    Error = "An error occurred while processing your request.",
                    SearchType = "Agentic AI Search",
                    Query = request?.Query ?? "",
                    Metadata = new SearchMetadata
                    {
                        ProcessingTimeMs = (int)stopwatch.ElapsedMilliseconds
                    }
                };
                
                return Json(errorResponse);
            }
        }

        [HttpPost("stream")]
        public async Task<IActionResult> StreamSearch([FromBody] AgenticSearchRequest request)
        {
            try
            {
                if (request == null || string.IsNullOrWhiteSpace(request.Query))
                {
                    return BadRequest("Invalid search request.");
                }

                _logger.LogInformation("Processing agentic streaming search query: {Query}", request.Query);

                // 设置SSE响应头
                Response.ContentType = "text/event-stream";
                Response.Headers["Cache-Control"] = "no-cache";
                Response.Headers["X-Accel-Buffering"] = "no";

                // 开始流式响应
                await foreach (var chunk in _agenticService.AgenticRetrieveStreamAsync(request.Query, request.SystemPrompt))
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
                _logger.LogError(ex, "Error processing agentic streaming search request: {Error}", ex.Message);
                await WriteSSEAsync("message", new { error = ex.Message });
                return new EmptyResult();
            }
        }

        [HttpPost("setup")]
        public async Task<IActionResult> SetupAgent()
        {
            try
            {
                _logger.LogInformation("Setting up knowledge agent");

                var result = await _agenticService.CreateKnowledgeAgentAsync();

                return Json(new { success = true, message = "Knowledge agent created successfully", result = result });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error setting up knowledge agent: {Error}", ex.Message);
                return Json(new { success = false, error = ex.Message });
            }
        }

        [HttpGet("status")]
        public async Task<IActionResult> GetAgentStatus()
        {
            try
            {
                _logger.LogInformation("Checking knowledge agent status");

                var result = await _agenticService.CheckKnowledgeAgentAsync();

                return Json(new { success = true, message = "Knowledge agent is available", result = result });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error checking knowledge agent status: {Error}", ex.Message);
                return Json(new { success = false, error = ex.Message });
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

    public class AgenticSearchRequest
    {
        public string Query { get; set; } = string.Empty;
        public string? SystemPrompt { get; set; }
    }
}
