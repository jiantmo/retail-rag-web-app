using Microsoft.AspNetCore.Mvc;
using retail_rag_web_app.Services;

namespace retail_rag_web_app.Controllers
{
    [ApiController]
    [Route("[controller]")]
    public class KnowledgeAgentController : ControllerBase
    {
        private readonly KnowledgeAgentManagementService _knowledgeAgentService;
        private readonly ILogger<KnowledgeAgentController> _logger;

        public KnowledgeAgentController(KnowledgeAgentManagementService knowledgeAgentService, ILogger<KnowledgeAgentController> logger)
        {
            _knowledgeAgentService = knowledgeAgentService;
            _logger = logger;
        }

        /// <summary>
        /// List all knowledge agents
        /// </summary>
        [HttpGet("list")]
        public async Task<IActionResult> ListAgents()
        {
            try
            {
                var agents = await _knowledgeAgentService.ListKnowledgeAgentsAsync();
                return Ok(new { success = true, agents = agents.Value });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to list knowledge agents");
                return BadRequest(new { success = false, error = ex.Message });
            }
        }

        /// <summary>
        /// Get a specific knowledge agent
        /// </summary>
        [HttpGet("get/{agentName?}")]
        public async Task<IActionResult> GetAgent(string agentName = null)
        {
            try
            {
                var agent = await _knowledgeAgentService.GetKnowledgeAgentAsync(agentName);
                if (agent == null)
                {
                    return NotFound(new { success = false, error = "Knowledge agent not found" });
                }
                return Ok(new { success = true, agent });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Failed to get knowledge agent: {agentName}");
                return BadRequest(new { success = false, error = ex.Message });
            }
        }

        /// <summary>
        /// Create a new knowledge agent
        /// </summary>
        [HttpPost("create")]
        public async Task<IActionResult> CreateAgent([FromBody] CreateAgentRequest request)
        {
            try
            {
                var options = new KnowledgeAgentCreateOptions
                {
                    DefaultRerankerThreshold = request.RerankerThreshold ?? 2.5,
                    DefaultIncludeReferenceSourceData = request.IncludeReferenceSourceData ?? true,
                    DefaultMaxDocsForReranker = request.MaxDocsForReranker ?? 200,
                    ModelName = !string.IsNullOrEmpty(request.ModelName) ? request.ModelName : "gpt-4.1",
                    MaxOutputSize = request.MaxOutputSize ?? 5000,
                    MaxRuntimeInSeconds = request.MaxRuntimeInSeconds ?? 60
                };

                var agent = await _knowledgeAgentService.CreateKnowledgeAgentAsync(request.AgentName, options);
                return Ok(new { success = true, message = "Knowledge agent created successfully", agent });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to create knowledge agent");
                return BadRequest(new { success = false, error = ex.Message });
            }
        }

        /// <summary>
        /// Delete a knowledge agent
        /// </summary>
        [HttpDelete("delete/{agentName?}")]
        public async Task<IActionResult> DeleteAgent(string agentName = null)
        {
            try
            {
                var success = await _knowledgeAgentService.DeleteKnowledgeAgentAsync(agentName);
                if (success)
                {
                    return Ok(new { success = true, message = "Knowledge agent deleted successfully" });
                }
                else
                {
                    return NotFound(new { success = false, error = "Knowledge agent not found" });
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Failed to delete knowledge agent: {agentName}");
                return BadRequest(new { success = false, error = ex.Message });
            }
        }

        /// <summary>
        /// Test a knowledge agent with a sample query
        /// </summary>
        [HttpPost("test")]
        public async Task<IActionResult> TestAgent([FromBody] TestAgentRequest request)
        {
            try
            {
                var query = string.IsNullOrEmpty(request.Query) ? "What products do you recommend?" : request.Query;
                var role = string.IsNullOrEmpty(request.Role) ? "user" : request.Role;
                
                // Validate role
                if (role != "user" && role != "assistant")
                {
                    return BadRequest(new { success = false, error = "Role must be either 'user' or 'assistant'" });
                }
                
                var result = await _knowledgeAgentService.TestKnowledgeAgentAsync(query, request.AgentName, role, request.AssistantContext);
                return Ok(new { success = true, result });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to test knowledge agent");
                return BadRequest(new { success = false, error = ex.Message });
            }
        }

        /// <summary>
        /// Setup and ensure knowledge agent exists with optimal settings
        /// </summary>
        [HttpPost("setup")]
        public async Task<IActionResult> SetupAgent([FromBody] SetupAgentRequest request = null)
        {
            try
            {
                // Create agent with optimal settings for retail
                var options = new KnowledgeAgentCreateOptions
                {
                    DefaultRerankerThreshold = 2.0,  // Lower threshold for retail queries
                    DefaultIncludeReferenceSourceData = true,
                    DefaultMaxDocsForReranker = 200,  // Increased for better retrieval coverage
                    ModelName = "gpt-4.1",  // Explicitly set model name
                    MaxOutputSize = 5000,
                    MaxRuntimeInSeconds = 30  // Faster response for retail
                };

                var agent = await _knowledgeAgentService.CreateKnowledgeAgentAsync(request?.AgentName, options);
                
                // Test the agent with graceful error handling
                string testStatus;
                string testMessage;
                try 
                {
                    var testResult = await _knowledgeAgentService.TestKnowledgeAgentAsync("What products are available?", request?.AgentName);
                    testStatus = "success";
                    testMessage = testResult?.Content?.Substring(0, Math.Min(200, testResult.Content?.Length ?? 0)) + "...";
                }
                catch (Exception testEx)
                {
                    _logger.LogWarning(testEx, "Knowledge agent test failed during setup, but agent was created successfully");
                    testStatus = "created_but_test_pending";
                    testMessage = "Knowledge agent created successfully. Testing may be temporarily unavailable due to permission propagation. Please try again in a few minutes.";
                }
                
                return Ok(new 
                { 
                    success = true, 
                    message = "Knowledge agent setup completed", 
                    agent,
                    testStatus,
                    testResult = testMessage
                });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to setup knowledge agent");
                return BadRequest(new { success = false, error = ex.Message });
            }
        }

        /// <summary>
        /// Get the status and health of knowledge agents
        /// </summary>
        [HttpGet("status")]
        public async Task<IActionResult> GetStatus()
        {
            try
            {
                // Check if default agent exists
                var agent = await _knowledgeAgentService.GetKnowledgeAgentAsync();
                
                if (agent != null)
                {
                    // Test the agent
                    try
                    {
                        var testResult = await _knowledgeAgentService.TestKnowledgeAgentAsync("Test query");
                        return Ok(new 
                        { 
                            success = true, 
                            status = "ready", 
                            agentName = agent.Name,
                            message = "Knowledge agent is operational",
                            lastTest = DateTime.UtcNow,
                            testPassed = !string.IsNullOrEmpty(testResult?.Content)
                        });
                    }
                    catch (Exception testEx)
                    {
                        _logger.LogWarning(testEx, "Knowledge agent exists but test failed");
                        return Ok(new 
                        { 
                            success = true, 
                            status = "exists-but-error", 
                            agentName = agent.Name,
                            message = "Knowledge agent exists but test failed",
                            error = testEx.Message
                        });
                    }
                }
                else
                {
                    return Ok(new 
                    { 
                        success = false, 
                        status = "not-found", 
                        message = "Knowledge agent not found. Use /setup to create one." 
                    });
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to get knowledge agent status");
                return Ok(new 
                { 
                    success = false, 
                    status = "error", 
                    message = "Failed to check knowledge agent status",
                    error = ex.Message 
                });
            }
        }
    }

    // Request models
    public class CreateAgentRequest
    {
        public string? AgentName { get; set; }
        public double? RerankerThreshold { get; set; }
        public bool? IncludeReferenceSourceData { get; set; }
        public int? MaxDocsForReranker { get; set; }
        public string? ModelName { get; set; }
        public int? MaxOutputSize { get; set; }
        public int? MaxRuntimeInSeconds { get; set; }
    }

    public class TestAgentRequest
    {
        public string? AgentName { get; set; }
        public string? Query { get; set; }
        public string? Role { get; set; } = "user";
        public string? AssistantContext { get; set; }
    }

    public class SetupAgentRequest
    {
        public string? AgentName { get; set; }
    }
}
