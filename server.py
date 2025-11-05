"""微信公众号文章解析 MCP Server - 基于 FastMCP 框架"""

import os
import json
import re
import logging
import time
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from fastmcp import FastMCP

# 创建 MCP 服务实例
mcp = FastMCP("wechat-article-parser-mcp-server")

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def error_response(code: str, message: str) -> str:
    """创建错误响应 JSON 字符串"""
    response = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }
    return json.dumps(response, ensure_ascii=False)

def validate_wechat_url(url: str) -> Tuple[bool, Optional[str]]:
    """验证微信公众号文章 URL，返回 (是否有效, 错误消息)"""
    if not url or not url.strip():
        return False, "URL cannot be empty. Please provide a valid WeChat article URL."
    
    # 检查是否是微信公众号文章 URL
    wechat_patterns = [
        r'https?://mp\.weixin\.qq\.com',
        r'https?://weixin\.qq\.com',
    ]
    
    is_wechat = any(re.search(pattern, url) for pattern in wechat_patterns)
    if not is_wechat:
        return False, "Invalid WeChat article URL. Please provide a URL from mp.weixin.qq.com"
    
    return True, None

def clean_html_content(html_content: str) -> str:
    """清理 HTML 内容，提取纯文本"""
    if not html_content:
        return ""
    
    # 使用 BeautifulSoup 解析并提取文本
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 移除脚本和样式标签
    for script in soup(["script", "style"]):
        script.decompose()
    
    # 获取文本并清理
    text = soup.get_text()
    
    # 清理多余的空白字符
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text


def parse_wechat_article(url: str, include_content: bool = False) -> Dict[str, Any]:
    """解析微信公众号文章，返回包含标题、作者、发布时间等信息的字典"""
    try:
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        logger.info(f"Fetching article from: {url}")
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取文章标题
        title = ""
        title_elem = soup.find('h1', class_='rich_media_title') or soup.find('h1', id='activity-name')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # 提取作者
        author = ""
        author_elem = soup.find('a', class_='rich_media_meta rich_media_meta_link rich_media_meta_nickname') or \
                     soup.find('strong', class_='profile_nickname') or \
                     soup.find('a', id='js_name')
        if author_elem:
            author = author_elem.get_text(strip=True)
        
        # 提取发布时间
        publish_time = ""
        time_elem = soup.find('em', class_='rich_media_meta rich_media_meta_text') or \
                   soup.find('span', class_='rich_media_meta rich_media_meta_text') or \
                   soup.find('em', id='publish_time')
        if time_elem:
            publish_time = time_elem.get_text(strip=True)
        
        # 提取文章正文（只关注文字内容）
        content_text = ""
        content_elem = soup.find('div', class_='rich_media_content') or \
                      soup.find('div', id='js_content')
        
        if content_elem:
            # 只获取纯文本内容，不关心 HTML 和图片
            content_text = clean_html_content(str(content_elem))
        
        # 提取文章摘要/描述
        description = ""
        desc_elem = soup.find('meta', property='og:description') or \
                   soup.find('meta', attrs={'name': 'description'})
        if desc_elem:
            description = desc_elem.get('content', '')
        
        # 构建返回结果
        result = {
            "success": True,
            "url": url,
            "title": title,
            "author": author,
            "publish_time": publish_time,
            "description": description,
            "metadata": {
                "charset": response.encoding,
                "content_type": response.headers.get('Content-Type', ''),
            }
        }
        
        # 只在需要时包含正文内容
        if include_content:
            result["content"] = {
                "text": content_text,
                "length": len(content_text)
            }
        else:
            # 只提供正文预览（前200字）
            result["content_preview"] = content_text[:200] + "..." if len(content_text) > 200 else content_text
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise Exception(f"Failed to fetch article: {str(e)}")
    except Exception as e:
        logger.error(f"Parsing error: {str(e)}")
        raise Exception(f"Failed to parse article: {str(e)}")

def generate_detailed_summary(content_text: str, title: str = "") -> str:
    """使用 LLM 生成详细摘要（至少十句话，总结全文和分段要点）"""
    if not content_text or len(content_text.strip()) < 100:
        return "文章内容过短，无法生成详细摘要。"
    
    try:
        # 构建提示词
        prompt = f"""请为以下文章生成详细摘要，要求：

**输出结构：**
1. 使用"**总论点**："作为标题，然后用1-2句话总结文章的核心观点
2. 使用"**分论点**："作为标题，然后按照文章的自然结构，逐一阐述各个分论点
3. 每个分论点用独立的自然段落表达，不使用列表符号（如 -、•、1. 2. 3. 等）

**必须做到：**
- 至少十句话，全面总结文章核心内容
- 清晰呈现总论点：用1-2句话明确表达文章的核心观点
- 按文章结构阐述分论点：根据文章的自然结构和逻辑顺序，用流畅的段落文字逐一阐述各个分论点
- 使用第三人称客观描述：使用"文章"、"作者"、"父亲"等第三人称，保持人称一致，绝对不要使用"你"、"他"、"爸爸"等，完全用第三人称客观转述
- 使用自然语言：每个分论点用独立的段落表达，不使用列表符号或编号，保持逻辑清晰、语言自然

**输出格式示例：**
**总论点**：
文章的核心观点是[用1-2句话表达核心观点]。

**分论点**：

[分论点1的段落文字，用第三人称客观描述（如"文章认为"、"作者指出"、"父亲希望"等），自然流畅的语言表达，绝对不要使用"你"、"他"等]

[分论点2的段落文字，用第三人称客观描述，自然流畅的语言表达]

[分论点3的段落文字，用第三人称客观描述，自然流畅的语言表达]

...

**注意：**
- 不要使用任何列表符号（-、•、1. 2. 3. 等）
- 必须使用"**总论点**："和"**分论点**："作为分段标题
- 每个分论点用独立的自然段落表达，段落之间空一行
- 使用第三人称客观描述，保持人称一致（如"文章"、"作者"、"父亲"等，绝对不要使用"你"、"他"、"爸爸"等，完全用第三人称客观转述）
- 完全使用自然段落文字，客观准确地呈现内容

文章标题：{title if title else '未提供'}

文章正文：
{content_text[:4000]}"""  # 限制长度，避免超出token限制
        
        # 调用 LLM 生成摘要
        summary = call_llm_api(
            prompt=prompt,
            model="glm-4",
            max_tokens=1500,
            temperature=0.3
        )
        
        return summary.strip()
        
    except Exception as e:
        logger.error(f"Failed to generate summary: {str(e)}")
        # 如果 LLM 调用失败，返回简单摘要
        if len(content_text) > 500:
            return content_text[:500] + "..."
        return content_text


@mcp.tool()
def parse_article(url: str, save_summary: Optional[str] = "true") -> str:
    """解析微信公众号文章，生成详细摘要（至少十句话，总结全文和分段要点），并自动保存为 Markdown 文件
    
    Args:
        url: 微信公众号文章 URL
        save_summary: 是否保存摘要为 Markdown 文件，可选 "true"/"false"（默认 "true"，自动保存）
    """
    try:
        logger.info(f"Article parsing request: url={url}, save_summary={save_summary}")
        
        # 验证 URL
        is_valid, error_msg = validate_wechat_url(url)
        if not is_valid:
            logger.warning(f"Invalid URL: {error_msg}")
            return error_response("INVALID_URL", error_msg)
        
        # 解析文章（需要完整正文来生成摘要）
        try:
            article_data = parse_wechat_article(url, include_content=True)
            
            if not article_data.get("success"):
                return error_response("PARSE_ERROR", "Failed to parse article.")
            
            # 获取文章内容（已经 include_content=True，所以一定有 content）
            content_text = article_data.get("content", {}).get("text", "")
            
            # 生成详细摘要
            logger.info("Generating detailed summary using LLM...")
            detailed_summary = generate_detailed_summary(
                content_text=content_text,
                title=article_data.get("title", "")
            )
            
            # 如果要求保存摘要，保存为 Markdown 文件
            file_path = None
            # 处理字符串参数（"true"/"false"）
            should_save = str(save_summary).lower() in ('true', '1', 'yes', 'on')
            if should_save:
                safe_title = "".join(c if c.isalnum() or c in ('-', '_', ' ') else '_' for c in article_data.get("title", "未命名文章"))
                safe_title = safe_title[:50]
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # 保存到项目根目录（/Users/yingzhang/Library/CloudStorage/Dropbox/Cursor2025）
                base_dir = Path("/Users/yingzhang/Library/CloudStorage/Dropbox/Cursor2025")
                output_path = base_dir / f"{safe_title}-摘要-{timestamp}.md"
                
                # 确保目录存在
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 构建 Markdown 内容
                summary_markdown = f"""# 文章摘要

**文章标题**: {article_data.get("title", "")}  
**作者**: {article_data.get("author", "")}  
**发布时间**: {article_data.get("publish_time", "")}  
**文章链接**: {url}  
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 详细摘要

{detailed_summary}

---

**注**: 本摘要由 LLM 生成，基于语义理解和深度分析。
"""
                
                # 保存文件
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(summary_markdown)
                    # 验证文件确实被保存
                    if output_path.exists():
                        file_path = str(output_path.absolute())  # 返回绝对路径
                        logger.info(f"Summary saved successfully to: {file_path}")
                    else:
                        logger.error(f"File write completed but file doesn't exist: {output_path}")
                        file_path = None
                except Exception as e:
                    logger.error(f"Failed to save summary file: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    file_path = None
            
            # 构建返回结果（只包含基本信息+详细摘要）
            result = {
                "success": True,
                "url": url,
                "title": article_data.get("title", ""),
                "author": article_data.get("author", ""),
                "publish_time": article_data.get("publish_time", ""),
                "summary": detailed_summary,
                "metadata": {
                    "charset": article_data.get("metadata", {}).get("charset", ""),
                    "content_type": article_data.get("metadata", {}).get("content_type", ""),
                }
            }
            
            # 如果保存了文件，添加文件路径
            if file_path:
                result["file_path"] = file_path
                result["file_size"] = Path(file_path).stat().st_size if Path(file_path).exists() else 0
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Parsing error: {str(e)}")
            error_str = str(e)
            if "404" in error_str or "Not Found" in error_str:
                return error_response("NOT_FOUND", "Article not found. Please check the URL.")
            elif "timeout" in error_str.lower():
                return error_response("TIMEOUT", "Request timed out. Please try again.")
            else:
                return error_response("PARSE_ERROR", f"Failed to parse article: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error in parse_article: {str(e)}")
        return error_response("INTERNAL_ERROR", "An unexpected error occurred. Please try again.")


def call_llm_api(prompt: str, model: str = "glm-4", max_tokens: int = 4000, temperature: float = 0.3) -> str:
    """调用智谱 AI API 进行分析"""
    try:
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            try:
                from config import ZHIPU_API_KEY
                api_key = ZHIPU_API_KEY
            except ImportError:
                pass
        if not api_key:
            raise Exception("ZHIPU_API_KEY not found. Please set ZHIPU_API_KEY environment variable in MCP configuration.")
        
        # 智谱 AI API endpoint
        api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位擅长分析微信公众号文章的专家，能够进行深入的语义分析、观点提取和结构分析。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        logger.info(f"Calling Zhipu AI API: model={model}, prompt_length={len(prompt)}")
        
        # 添加重试机制
        max_retries = 3
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    api_url,
                    json=payload,
                    headers=headers,
                    timeout=120
                )
                break  # 成功则退出循环
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避：2秒、4秒、8秒
                    logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
        
        # 如果所有重试都失败，抛出最后一个异常
        if last_exception:
            raise last_exception
        
        response.raise_for_status()
        result = response.json()
        
        # 智谱 AI API 响应格式
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            logger.info(f"Zhipu AI API response received, length={len(content)}")
            return content
        else:
            raise Exception("Invalid response from Zhipu AI API")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM API request error: {str(e)}")
        raise Exception(f"Failed to call LLM API: {str(e)}")
    except Exception as e:
        logger.error(f"LLM API error: {str(e)}")
        raise


@mcp.tool()
def analyze_with_llm(
    url: Optional[str] = None, title: Optional[str] = None, author: Optional[str] = None,
    content: Optional[str] = None, save_path: Optional[str] = None,
    model: Optional[str] = "glm-4", analysis_type: Optional[str] = "comprehensive"
) -> str:
    """使用智谱 AI 进行深度语义分析和观点提取。可基于 URL 自动解析或直接提供内容。"""
    try:
        logger.info(f"LLM analysis request: url={url}, type={analysis_type}, model={model}")
        
        article_data = None
        final_title = title
        final_author = author or ""
        final_content = content
        final_description = ""
        
        # 如果提供了 URL，先解析文章
        if url:
            is_valid, error_msg = validate_wechat_url(url)
            if not is_valid:
                logger.warning(f"Invalid URL: {error_msg}")
                return error_response("INVALID_URL", error_msg)
            
            try:
                # 需要完整内容进行分析，所以 include_content=True
                article_data = parse_wechat_article(url, include_content=True)
                if not article_data.get("success"):
                    return error_response("PARSE_ERROR", "Failed to parse article from URL.")
                
                final_title = article_data.get("title", title or "未命名文章")
                final_author = article_data.get("author", author or "")
                # 获取完整正文内容（已经 include_content=True）
                final_content = article_data.get("content", {}).get("text", content or "")
                final_description = article_data.get("description", "")
                
            except Exception as e:
                logger.error(f"Failed to parse article: {str(e)}")
                return error_response("PARSE_ERROR", f"Failed to parse article: {str(e)}")
        
        # 验证必需参数
        if not final_content:
            return error_response("MISSING_CONTENT", "Article content is required. Please provide either URL or content parameter.")
        
        if not final_title:
            final_title = "未命名文章"
        
        # 根据分析类型构建不同的提示词
        if analysis_type == "viewpoint":
            prompt = f"""请对以下微信公众号文章进行观点提取和分析：

**文章标题**: {final_title}
**作者**: {final_author}
**文章内容**:
{final_content[:6000]}

请完成以下分析：

1. **核心观点识别**：提取文章的核心观点（1-2句话）
2. **分论点链条**：识别文章的主要分论点（3-5个），并说明它们如何支撑核心观点
3. **论证方式**：分析文章使用了哪些论证方式（案例、数据、引用、故事等）
4. **观点价值评估**：评估核心观点和分论点的价值（1-5分，说明理由）
5. **逻辑结构**：分析文章的逻辑结构是否清晰，是否存在逻辑跳跃

请以 Markdown 格式输出，包含表格和结构化内容。"""
        
        elif analysis_type == "structure":
            prompt = f"""请对以下微信公众号文章进行结构分析：

**文章标题**: {final_title}
**作者**: {final_author}
**文章内容**:
{final_content[:6000]}

请完成以下分析：

1. **文章结构**：分析文章的整体结构（开头、主体、结尾）
2. **段落组织**：分析段落之间的逻辑关系
3. **过渡衔接**：评估段落之间的过渡是否自然
4. **层次划分**：识别文章的信息层次（标题、小标题、段落等）
5. **可读性**：评估文章的可读性，给出改进建议

请以 Markdown 格式输出。"""
        
        else:  # comprehensive
            prompt = f"""请对以下微信公众号文章进行深度综合分析：

**文章标题**: {final_title}
**作者**: {final_author}
**文章内容**:
{final_content[:6000]}

请完成以下综合分析：

## 1. 核心观点提取
- 核心观点（1-2句话）
- 分论点链条（3-5个主要分论点）
- 观点之间的逻辑关系

## 2. 结构分析
- 文章整体结构（开头、主体、结尾）
- 段落组织与逻辑关系
- 过渡衔接是否自然

## 3. 论证方式分析
- 使用的论证方式（案例、数据、引用、故事、对比等）
- 每种论证方式的效果评估

## 4. 语言风格分析
- 语言特点（简洁/冗长、生动/平淡、专业/通俗等）
- 表达技巧（修辞手法、金句等）
- 可读性评估

## 5. 价值与影响评估
- 观点价值（创新性、实用性、传播价值）
- 目标读者群体
- 可能的传播效果

请以 Markdown 格式输出，使用表格和结构化内容，确保分析深入、具体、可操作。不要包含优化建议部分。

**重要**：直接输出 Markdown 内容，不要使用代码块（```）包裹。表格应该直接使用 Markdown 表格语法。"""
        
        # 调用 LLM API
        try:
            logger.info(f"Calling LLM for analysis: type={analysis_type}, model={model}, content_length={len(final_content)}")
            analysis_result = call_llm_api(
                prompt=prompt,
                model=model,
                max_tokens=4000,
                temperature=0.3
            )
            
            # 处理 LLM 返回的结果，移除可能的代码块包裹
            # 移除开头的代码块标记（可能是 ``` 或 ```markdown 等）
            analysis_result = re.sub(r'^```[\w]*\s*\n?', '', analysis_result.strip(), flags=re.MULTILINE)
            # 移除结尾的代码块标记
            analysis_result = re.sub(r'\n?```\s*$', '', analysis_result, flags=re.MULTILINE)
            # 移除中间的代码块标记（如果 LLM 在内容中间也加了标记）
            analysis_result = re.sub(r'```[\w]*\s*\n', '', analysis_result)
            analysis_result = re.sub(r'\n```\s*\n', '\n', analysis_result)
            analysis_result = analysis_result.strip()
            
            # 构建完整的分析报告
            analysis_markdown = f"""# LLM 深度分析报告（微信公众号文章）

**文章标题**: {final_title}  
**作者**: {final_author}  
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**分析类型**: {analysis_type}  
**使用模型**: {model}  
**文章统计**: 总字数约 {len(final_content)} 字

---

{analysis_result}

---

**注**: 本分析由 LLM 生成，基于语义理解和深度推理。如需更精确的分析，建议结合人工审核。
"""
            
            # 确定保存路径（与 parse_article 保持一致）
            if save_path:
                output_path = Path(save_path)
            else:
                # 自动生成文件名，保存到项目根目录（添加时间戳）
                safe_title = "".join(c if c.isalnum() or c in ('-', '_', ' ') else '_' for c in final_title)
                safe_title = safe_title[:50]
                analysis_type_cn = {
                    "comprehensive": "综合分析",
                    "viewpoint": "观点提取",
                    "structure": "结构分析"
                }.get(analysis_type, "分析")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_dir = Path("/Users/yingzhang/Library/CloudStorage/Dropbox/Cursor2025")
                output_path = base_dir / f"{safe_title}-LLM{analysis_type_cn}-{timestamp}.md"
            
            # 确保目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(analysis_markdown)
            
            logger.info(f"LLM analysis saved to: {output_path}")
            
            # 返回结果
            result = {
                "success": True,
                "message": "LLM analysis completed successfully",
                "file_path": str(output_path),
                "file_size": output_path.stat().st_size if output_path.exists() else 0,
                "article_info": {
                    "title": final_title,
                    "author": final_author,
                    "content_length": len(final_content)
                },
                "analysis_info": {
                    "type": analysis_type,
                    "model": model,
                    "provider": "zhipu",
                    "method": "LLM semantic analysis"
                }
            }
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Failed to call LLM API: {str(e)}")
            error_msg = str(e)
            if "ZHIPU_API_KEY" in error_msg or "API key" in error_msg.lower():
                return error_response("API_KEY_ERROR", "Zhipu AI API key not found. Please set ZHIPU_API_KEY environment variable in MCP configuration.")
            else:
                return error_response("LLM_ERROR", f"Failed to analyze with Zhipu AI: {error_msg}")
    
    except Exception as e:
        logger.error(f"Unexpected error in analyze_with_llm: {str(e)}")
        return error_response("INTERNAL_ERROR", "An unexpected error occurred. Please try again.")


if __name__ == "__main__":
    mcp.run()

