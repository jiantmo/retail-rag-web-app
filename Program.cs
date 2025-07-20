using dotenv.net;

// Load .env file
DotEnv.Load();

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllersWithViews();

// Add HttpClient service
builder.Services.AddHttpClient();

// Register custom services
builder.Services.AddScoped<retail_rag_web_app.Services.RagService>();
builder.Services.AddScoped<retail_rag_web_app.Services.AgenticSearchService>();
builder.Services.AddScoped<retail_rag_web_app.Services.AgenticRetrievalService>();
builder.Services.AddScoped<retail_rag_web_app.Services.KnowledgeAgentManagementService>();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
    // The default HSTS value is 30 days. You may want to change this for production scenarios.
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();

app.UseRouting();

app.UseAuthorization();

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.Run();
