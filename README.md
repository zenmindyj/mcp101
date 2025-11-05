# 微信公众号文章解析 MCP Server

基于 FastMCP 框架实现的微信公众号文章内容解析 MCP（Model Context Protocol）服务器。

## 功能特性

- ✅ 解析微信公众号文章 URL
- ✅ 提取文章标题、作者、发布时间
- ✅ 提取文章正文（纯文本格式）
- ✅ 提取文章摘要/描述
- ✅ **LLM 深度分析**：使用大语言模型进行语义分析、观点提取、结构分析
- ✅ 专注于文字内容解析，不处理图片
- ✅ 基于 FastMCP 框架，使用 stdio 传输
- ✅ 遵循 MCP 规范，与所有 MCP 客户端兼容

## 环境准备

### 1. 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

如果网络较慢，可以使用国内镜像源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 运行服务

```bash
python server.py
```

## 在 Cursor 中配置 MCP

编辑 `~/.cursor/mcp.json`，添加以下配置：

```json
{
  "mcpServers": {
    "wechat-article-parser": {
      "command": "python3",
      "args": ["/绝对路径/wechat-article-parser-mcp/server.py"]
    }
  }
}
```

重启 Cursor，即可使用微信公众号文章解析功能！

### 配置 LLM API（可选，用于深度分析）

如果需要使用 `analyze_with_llm` 工具，需要配置智谱 AI API Key。

**配置方式：环境变量（在 MCP 配置中）**

在 `~/.cursor/mcp.json` 中配置 API Key（已在安装步骤中配置）：

```json
{
  "wechat-article-parser": {
    "command": "python3",
    "args": ["/path/to/server.py"],
    "env": {
      "ZHIPU_API_KEY": "your-zhipu-api-key-here"
    }
  }
}
```

**获取 API Key：**
访问 https://open.bigmodel.cn/ 注册并获取 API Key

## 可用工具

### parse_article

解析微信公众号文章，生成详细摘要（使用 LLM 生成至少十句话的摘要，总结全文和分段要点）。

**参数：**
- `url` (必填): 微信公众号文章 URL，例如：`https://mp.weixin.qq.com/s/...`

**返回示例：**
```json
{
  "success": true,
  "url": "https://mp.weixin.qq.com/s/...",
  "title": "文章标题",
  "author": "作者名称",
  "publish_time": "2024-01-01 12:00:00",
  "summary": "使用 LLM 生成的详细摘要（至少十句话，总结全文和分段要点）...",
  "metadata": {
    "charset": "utf-8",
    "content_type": "text/html"
  }
}
```

**使用示例：**
```
parse_article(
    url="https://mp.weixin.qq.com/s/xxxxx"
)
```

### analyze_with_llm

使用大语言模型进行深度语义分析和观点提取（推荐）。

**参数：**
- `url` (可选): 微信公众号文章 URL，如果提供则自动解析文章内容
- `title` (可选): 文章标题，如果不提供 URL 则必须提供
- `author` (可选): 作者名称
- `content` (可选): 文章正文内容，如果不提供 URL 则必须提供
- `save_path` (可选): 保存分析结果的 Markdown 文件路径，如果不提供则自动生成文件名
- `model` (可选): LLM 模型名称，默认 "glm-4"，可选 "glm-4-flash", "glm-3-turbo" 等（智谱 AI）
- `analysis_type` (可选): 分析类型，默认 "comprehensive"（综合分析），可选 "viewpoint"（观点提取）、"structure"（结构分析）

**分析类型说明：**
- **comprehensive**（综合分析）：完整分析，包括观点、结构、论证方式、语言风格、价值评估
- **viewpoint**（观点提取）：专注于观点提取和分析，包括核心观点、分论点链条、论证方式、观点价值
- **structure**（结构分析）：专注于文章结构分析，包括整体结构、段落组织、过渡衔接、层次划分、可读性

**返回示例：**
```json
{
  "success": true,
  "message": "LLM analysis completed successfully",
  "file_path": "文章标题-LLM综合分析.md",
  "file_size": 12345,
  "article_info": {
    "title": "文章标题",
    "author": "作者名称",
    "content_length": 1234
  },
    "analysis_info": {
      "type": "comprehensive",
      "model": "glm-4",
      "provider": "zhipu",
      "method": "LLM semantic analysis"
    }
}
```

**使用示例：**

方式 1：综合分析（默认）
```
analyze_with_llm(
    url="https://mp.weixin.qq.com/s/xxxxx"
)
```

方式 2：只提取观点
```
analyze_with_llm(
    url="https://mp.weixin.qq.com/s/xxxxx",
    analysis_type="viewpoint"
)
```

方式 3：只分析结构
```
analyze_with_llm(
    url="https://mp.weixin.qq.com/s/xxxxx",
    analysis_type="structure"
)
```

方式 4：指定分析类型和模型
```
analyze_with_llm(
    url="https://mp.weixin.qq.com/s/xxxxx",
    model="glm-4",
    analysis_type="viewpoint"
)
```

方式 5：使用不同的模型
```
analyze_with_llm(
    url="https://mp.weixin.qq.com/s/xxxxx",
    model="glm-4-flash"
)
```

**注意**：此工具需要智谱 AI API Key，会产生 API 调用费用。推荐使用 `glm-4` 模型，国内服务稳定且成本较低。

## 使用场景

### 场景 1：快速获取文章摘要

使用 `parse_article` 工具，快速获取文章标题、作者、发布时间，以及使用 LLM 生成的详细摘要（至少十句话，总结全文和分段要点）。

### 场景 2：LLM 深度分析（推荐）

使用 `analyze_with_llm` 工具进行深度语义分析：
- **观点提取**：自动识别核心观点和分论点链条
- **结构分析**：分析文章结构、段落组织、逻辑关系
- **论证方式**：识别使用的论证方式并评估效果
- **语言风格**：分析语言特点、表达技巧、可读性
- **价值评估**：评估观点价值、传播潜力、目标读者

## 技术实现

### 核心技术栈

- **FastMCP**: MCP 服务器框架
- **requests**: HTTP 请求库
- **BeautifulSoup4**: HTML 解析库
- **lxml**: XML/HTML 解析器（BeautifulSoup 后端）

### 解析流程

1. **URL 验证**：验证是否为有效的微信公众号文章 URL
2. **HTTP 请求**：使用 requests 发送 GET 请求，模拟浏览器访问
3. **HTML 解析**：使用 BeautifulSoup 解析 HTML 内容
4. **信息提取**：
   - 标题：从 `<h1>` 标签提取
   - 作者：从作者相关的 CSS 类提取
   - 发布时间：从时间相关的标签提取
   - 正文：从 `rich_media_content` 或 `js_content` 提取纯文本
   - 摘要：从 meta 标签提取
5. **内容清理**：移除 HTML 标签、脚本、样式，提取纯文本
6. **LLM 摘要生成**（parse_article）：使用 LLM 生成详细摘要（至少十句话，总结全文和分段要点）
7. **结果返回**：返回 JSON 格式的结构化数据

## 注意事项

1. **反爬虫机制**：微信公众号可能有反爬虫机制，建议：
   - 控制请求频率
   - 使用合适的 User-Agent
   - 避免频繁请求同一公众号

2. **内容合法性**：确保解析和使用微信公众号文章内容符合相关法律法规和平台规定。

3. **URL 格式**：确保提供的是完整的微信公众号文章 URL，格式通常为：
   - `https://mp.weixin.qq.com/s/xxxxx`
   - `https://weixin.qq.com/s/xxxxx`

4. **内容更新**：微信公众号文章内容可能会更新，解析结果可能因时间而异。

## 开发

### 运行测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=server --cov-report=html

# 运行类型检查
mypy server.py
```

### 项目结构

```
.
├── server.py              # MCP 服务器主程序
├── requirements.txt       # Python 依赖包
├── README.md              # 项目文档（本文件）
├── .gitignore             # Git 忽略文件
└── tests/                 # 测试目录（可选）
    └── test_server.py      # 服务器单元测试
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

