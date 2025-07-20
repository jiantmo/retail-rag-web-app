# Retail RAG Web App

这是一个基于 Azure AI Search 和 Azure OpenAI 的零售产品推荐网站。用户可以通过自然语言查询来搜索产品并获得智能推荐。

## 功能特点

- 🛍️ **智能产品搜索**: 使用自然语言搜索产品
- 🤖 **AI 驱动的推荐**: 基于 Azure OpenAI 的智能推荐系统
- 🔍 **语义搜索**: 使用 Azure AI Search 的向量搜索功能
- 💬 **对话式界面**: 类似 ChatGPT 的用户体验
- 📱 **现代化 UI**: 响应式设计，支持移动设备

## 技术栈

- **后端**: ASP.NET Core 6.0
- **前端**: HTML5, CSS3, JavaScript (Vanilla)
- **AI 服务**: Azure OpenAI, Azure AI Search
- **身份验证**: Azure Identity (DefaultAzureCredential)

## 项目结构

```
retail-rag-web-app/
├── src/
│   ├── Controllers/
│   │   ├── HomeController.cs          # 主页控制器
│   │   └── SearchController.cs        # 搜索控制器（可选）
│   ├── Models/
│   │   └── SearchRequest.cs           # 搜索请求模型
│   ├── Services/
│   │   └── KnowledgeAgentService.cs   # Azure AI Search 代理服务
│   ├── Views/
│   │   ├── Home/
│   │   │   └── Index.cshtml           # 主页视图
│   │   └── Shared/
│   │       └── _Layout.cshtml         # 布局模板
│   ├── wwwroot/
│   │   ├── css/
│   │   │   └── site.css               # 样式文件
│   │   └── js/
│   ├── appsettings.json
│   ├── appsettings.Development.json
│   └── Program.cs                     # 应用程序入口点
├── .env                               # 环境变量配置
├── retail-rag-web-app.csproj         # 项目文件
└── README.md
```

## 安装和配置

### 1. 前提条件

- .NET 6.0 SDK
- Azure 订阅
- Azure AI Search 服务 (Basic 层级或更高)
- Azure OpenAI 服务

### 2. Azure 资源配置

1. **创建 Azure AI Search 服务**
   - 启用语义排序功能
   - 创建一个知识代理 (Knowledge Agent)
   - 创建搜索索引

2. **部署 Azure OpenAI 模型**
   - `gpt-4o` 或 `gpt-4o-mini` (用于查询规划和答案生成)
   - `text-embedding-3-large` (用于向量搜索)

3. **配置角色权限**
   - Search Service Contributor
   - Search Index Data Contributor
   - Search Index Data Reader
   - Cognitive Services User (对于 Azure OpenAI)

### 3. 环境变量配置

更新 `.env` 文件：

```env
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com
AZURE_SEARCH_INDEX_NAME=your-index-name
```

### 4. 运行应用程序

```bash
# 克隆项目
git clone <repository-url>
cd retail-rag-web-app

# 安装依赖
dotnet restore

# 编译项目
dotnet build

# 运行应用程序
dotnet run
```

应用程序将在 `https://localhost:5001` 或 `http://localhost:5000` 启动。

## 部署选项

### 开发环境
- **自托管**: `dotnet run` (推荐用于开发)
- **Visual Studio**: F5 调试运行
- **VS Code**: 使用调试配置

### 生产环境
1. **自托管 (推荐)**
   ```bash
   dotnet publish -c Release
   dotnet YourApp.dll
   ```

2. **IIS 部署 (传统方式)**
   - 安装 ASP.NET Core Hosting Bundle
   - 配置 web.config
   - 部署到 IIS 站点

3. **Docker 容器**
   ```dockerfile
   FROM mcr.microsoft.com/dotnet/aspnet:6.0
   COPY . /app
   WORKDIR /app
   ENTRYPOINT ["dotnet", "retail-rag-web-app.dll"]
   ```

4. **云部署**
   - Azure App Service
   - AWS Elastic Beanstalk
   - Google Cloud Run

### 为什么不再需要 IIS？
- ✅ **Kestrel** 是高性能的跨平台 Web 服务器
- ✅ **自包含部署** - 应用包含所有依赖
- ✅ **跨平台** - Windows、Linux、macOS
- ✅ **容器友好** - 原生支持 Docker
- ✅ **云原生** - 适合微服务架构

## 使用方法

1. 打开浏览器访问应用程序
2. 在搜索框中输入您的查询，例如：
   - "我需要给喜欢烹饪的爸爸买生日礼物"
   - "推荐一些户外运动装备"
   - "有什么适合儿童的玩具？"
3. 点击"搜索"按钮或按 Enter 键
4. 查看 AI 生成的产品推荐

## API 端点

### POST `/Home/Search`

搜索产品并获取 AI 推荐。

**请求体:**
```json
{
  "query": "用户搜索查询"
}
```

**响应:**
```json
{
  "success": true,
  "result": "AI 生成的推荐结果"
}
```

## Project Structure
```
retail-rag-web-app
├── src
│   ├── Controllers
│   │   └── SearchController.cs
│   ├── Models
│   │   └── SearchRequest.cs
│   ├── Services
│   │   └── KnowledgeAgentService.cs
│   ├── wwwroot
│   │   ├── css
│   │   │   └── site.css
│   │   └── js
│   │       └── site.js
│   ├── Views
│   │   ├── Home
│   │   │   └── Index.cshtml
│   │   └── Shared
│   │       └── _Layout.cshtml
│   ├── appsettings.json
│   ├── appsettings.Development.json
│   └── Program.cs
├── retail-rag-web-app.csproj
├── .env
└── README.md
```

## Setup Instructions
1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd retail-rag-web-app
   ```

2. **Install Dependencies**
   Ensure you have the .NET SDK installed. Run the following command to restore the project dependencies:
   ```bash
   dotnet restore
   ```

3. **Configure Environment Variables**
   Create a `.env` file in the root directory and set the following environment variables:
   ```
   AZURE_SEARCH_ENDPOINT=<your-azure-search-endpoint>
   AZURE_OPENAI_ENDPOINT=<your-azure-openai-endpoint>
   AZURE_SEARCH_INDEX_NAME=<your-index-name>
   ```

4. **Run the Application**
   You can run the application using the following command:
   ```bash
   dotnet run
   ```

5. **Access the Application**
   Open your web browser and navigate to `http://localhost:5000` to access the search interface.

## Usage
- Enter your search query in the text box and click the search button.
- The application will process your query and return relevant product recommendations based on the Azure Search service.

## Contributing
Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.