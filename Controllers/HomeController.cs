using Microsoft.AspNetCore.Mvc;
using retail_rag_web_app.Models;
using retail_rag_web_app.Services;

namespace retail_rag_web_app.Controllers
{
    public class HomeController : Controller
    {
        private readonly RagService _ragService;

        public HomeController(RagService ragService)
        {
            _ragService = ragService;
        }

        public IActionResult Index()
        {
            // Redirect to search controller
            return Redirect("/search");
        }

        public IActionResult KnowledgeAgent()
        {
            return View();
        }

        [HttpPost]
        public async Task<IActionResult> Search([FromBody] SearchRequest request)
        {
            try
            {
                var result = await _ragService.SearchAsync(request.Query);
                return Json(new { success = true, result });
            }
            catch (Exception ex)
            {
                return Json(new { success = false, error = ex.Message });
            }
        }
    }
}
