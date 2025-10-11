"""Search and URL reading tools for Axion Swarm specialists.

Specialists can use @[Search][query] syntax to perform real-time LLM-optimized searches.
Specialists can use @[ReadURL][url] to fetch full page content from specific URLs.

Search results and URL content are added to the conversation as tool messages.

Tavily is a search API specifically designed for LLM applications, providing
structured, citation-ready results optimized for AI agents.

Jina AI Reader extracts clean, LLM-friendly content from web pages, handling
JavaScript-heavy sites and removing ads/navigation/boilerplate.

Documentation: 
- Tavily: https://docs.tavily.com
- Jina Reader: https://jina.ai/reader/
"""

import os
import re
import sys
import html
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from langchain_core.messages import AIMessage


def detect_search_requests(message_content: str) -> List[str]:
    """Extract @[Search][query] mentions from specialist message.
    
    Pattern: @[Search][exact query text]
    
    Args:
        message_content: The specialist's message content
        
    Returns:
        List of search queries (the text inside second brackets)
        
    Examples:
        "@[Search][topic pricing details]" -> ["topic pricing details"]
        "@[Search][subject A details] and @[Search][subject B guidelines]" -> ["subject A details", "subject B guidelines"]
    """
    # Pattern: @[Search][query text here]
    # Captures the query text between the second set of brackets
    pattern = r'@\[Search\]\[([^\]]+)\]'
    matches = re.findall(pattern, message_content, re.IGNORECASE)
    return [query.strip() for query in matches if query.strip()]


def detect_readurl_requests(message_content: str) -> List[str]:
    """Extract @[ReadURL][url] mentions from specialist message.
    
    Pattern: @[ReadURL][url]
    
    Args:
        message_content: The specialist's message content
        
    Returns:
        List of URLs to read (the text inside second brackets)
        
    Examples:
        "@[ReadURL][https://example.com/article]" -> ["https://example.com/article"]
        "@[ReadURL][https://a.com] and @[ReadURL][https://b.com]" -> ["https://a.com", "https://b.com"]
    """
    # Pattern: @[ReadURL][url here]
    # Captures the URL between the second set of brackets
    pattern = r'@\[ReadURL\]\[([^\]]+)\]'
    matches = re.findall(pattern, message_content, re.IGNORECASE)
    return [url.strip() for url in matches if url.strip()]


def normalize_unicode_punctuation(text: str) -> str:
    """Normalize Unicode punctuation to ASCII equivalents.
    
    Converts smart quotes, em/en dashes, ellipsis, and other Unicode
    punctuation to their ASCII equivalents for better compatibility.
    
    Args:
        text: Text with potential Unicode punctuation
        
    Returns:
        Text with ASCII punctuation
    """
    # Smart quotes → straight quotes
    text = text.replace('\u201C', '"').replace('\u201D', '"')  # " and "
    text = text.replace('\u2018', "'").replace('\u2019', "'")  # ' and '
    text = text.replace('\u201E', '"').replace('\u201F', '"')  # „ and ‟
    text = text.replace('\u2032', "'").replace('\u2033', '"')  # ′ and ″ (primes)
    
    # Em dash and en dash → hyphen
    text = text.replace('\u2014', '-')  # em dash —
    text = text.replace('\u2013', '-')  # en dash –
    
    # Ellipsis → three dots
    text = text.replace('\u2026', '...')  # …
    
    # Other common Unicode punctuation → ASCII
    text = text.replace('\u00AB', '"').replace('\u00BB', '"')  # « and »
    text = text.replace('\u2022', '*')  # bullet •
    text = text.replace('\u00B7', '*')  # middle dot ·
    text = text.replace('\u2010', '-').replace('\u2011', '-')  # hyphens
    text = text.replace('\u00A0', ' ')  # non-breaking space → regular space
    
    return text


def clean_search_content(content: str) -> str:
    """Clean search result content to plain text only.
    
    Removes all formatting and artifacts while preserving the actual text content:
    - All markdown formatting (images, bold, italic, headers, code blocks, etc.)
    - HTML tags
    - Special characters used for formatting
    - Excessive whitespace
    
    Decodes HTML entities to proper Unicode characters.
    
    Args:
        content: Raw content from Tavily
        
    Returns:
        Plain text content suitable for specialist consumption
    """
    import re
    import html as html_module
    
    # Decode HTML entities first (&#x27; → ', &amp; → &, etc.)
    content = html_module.unescape(content)
    
    # Normalize Unicode punctuation to ASCII equivalents
    content = normalize_unicode_punctuation(content)
    
    # Remove HTML tags (in case any leaked through)
    content = re.sub(r'<[^>]+>', '', content)
    
    # Remove markdown images: ![alt](url) and [![text](url)
    content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', content)
    
    # Remove markdown links but keep the link text: [text](url) → text
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
    
    # Remove broken/incomplete markdown link syntax (leftover brackets, parentheses)
    # Aggressively remove patterns like: [](https: or [.webp) or [ [ [ [
    content = re.sub(r'\[\]\([^\s]*', '', content)  # Empty links: [](url
    content = re.sub(r'\[[^\]]{0,10}\)', '', content)  # Broken closing: [.webp) or [text)
    content = re.sub(r'(?<!\w)\[(?!\w)', '', content)  # Standalone opening brackets
    content = re.sub(r'(?<!\w)\](?!\w)', '', content)  # Standalone closing brackets
    content = re.sub(r'\s+\[\s+', ' ', content)  # Spaced brackets: [ text
    
    # Remove trailing ) that are markdown leftovers (often after URLs/filenames)
    # Pattern: word character followed by ) and then end of string or whitespace
    content = re.sub(r'\)(?=\s|$)', '', content)  # Trailing ) before space or end
    
    # Remove markdown headers: ## Header → Header (both at start of line and inline)
    content = re.sub(r'#+\s+', '', content)
    
    # Remove markdown bold/italic: **text** or *text* or __text__ or _text_ → text
    # Process iteratively to handle nested formatting
    for _ in range(3):  # Multiple passes to handle nested/adjacent formatting
        content = re.sub(r'\*\*([^\*]+)\*\*', r'\1', content)
        content = re.sub(r'__([^_]+)__', r'\1', content)
        content = re.sub(r'\*([^\*\n]+)\*', r'\1', content)
        content = re.sub(r'_([^_\n]+)_', r'\1', content)
    
    # Remove any remaining standalone asterisks or underscores (from broken formatting)
    content = re.sub(r'(?<!\w)[\*_]+(?!\w)', '', content)
    
    # Remove markdown code blocks: ```code``` or `code` → code
    content = re.sub(r'```[^\n]*\n([^`]+)```', r'\1', content)
    content = re.sub(r'`([^`]+)`', r'\1', content)
    
    # Remove markdown horizontal rules: --- or *** or ___
    content = re.sub(r'^[\-\*_]{3,}\s*$', '', content, flags=re.MULTILINE)
    
    # Remove markdown blockquotes: > text → text
    content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)
    
    # Remove markdown list markers: -, *, +, 1., etc.
    content = re.sub(r'^[\s]*[\-\*\+•]\s+', '', content, flags=re.MULTILINE)
    content = re.sub(r'^[\s]*\d+[\.)]\s+', '', content, flags=re.MULTILINE)
    
    # Remove common navigation artifacts
    content = re.sub(r'—\s*you are here\s*', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\s*›\s*', ' ', content)  # Breadcrumb separators
    content = re.sub(r'\s*»\s*', ' ', content)
    content = re.sub(r'\s*/\s*', ' ', content)  # Path separators (only isolated ones)
    
    # Remove standalone URLs (often leftover from image/link cleanup)
    content = re.sub(r'^[\s]*https?://[^\s]+[\s]*$', '', content, flags=re.MULTILINE)
    
    # Remove empty lines created by removals above
    content = re.sub(r'\n\s*\n+', ' ', content)
    
    # Collapse multiple spaces to single space
    content = re.sub(r'\s+', ' ', content)
    
    # Remove leading/trailing whitespace
    content = content.strip()
    
    # Remove duplicate consecutive sentences/phrases (common in navigation/breadcrumbs)
    # Split by sentence boundaries and deduplicate adjacent duplicates
    words = content.split()
    if len(words) > 10:  # Only dedupe if content is substantial
        # Look for repeated sequences of 4+ words
        i = 0
        deduped = []
        while i < len(words):
            # Check if we can find a repeating pattern starting here
            found_repeat = False
            for pattern_len in range(10, 3, -1):  # Check patterns from 10 words down to 4
                if i + pattern_len * 2 <= len(words):
                    pattern = words[i:i+pattern_len]
                    next_segment = words[i+pattern_len:i+pattern_len*2]
                    if pattern == next_segment:
                        # Found a repeat, add pattern once and skip the duplicate
                        deduped.extend(pattern)
                        i += pattern_len * 2
                        found_repeat = True
                        break
            
            if not found_repeat:
                deduped.append(words[i])
                i += 1
        
        content = ' '.join(deduped)
    
    # Remove standalone URLs that add no informational value
    # Full URLs: https://example.com/path or www.example.com
    content = re.sub(r'\bhttps?://\S+', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\bwww\.\S+', '', content, flags=re.IGNORECASE)
    
    # Query string fragments (no context, pure noise)
    # Patterns like: ?utm=value or &key=value or standalone key=value
    content = re.sub(r'[?&]\w+=[^\s&]*', '', content)  # ?key=value or &key=value
    content = re.sub(r'\b\w+source=\S+', '', content)  # utm patterns specifically
    
    # Image/media file references with no context
    content = re.sub(r'\S+\.(jpg|jpeg|png|gif|webp|svg|pdf)\b', '', content, flags=re.IGNORECASE)
    
    # Final cleanup: collapse whitespace
    content = re.sub(r'\s+', ' ', content)
    content = content.strip()
    
    # If empty after cleaning, nothing useful was there
    if not content:
        return "Content not available after cleaning web artifacts."
    
    # Content must contain actual words (2+ consecutive letters)
    # This catches cases where only numbers/punctuation remain
    has_readable_text = bool(re.search(r'[a-zA-Z]{2,}', content))
    
    if not has_readable_text:
        return "Content not available after cleaning web artifacts."
    
    # Check if content is only URL fragments (domains, paths) with no prose
    # Split into tokens and check if they're all URL-like components
    tokens = content.split()
    
    # Count tokens that look like URL components vs actual prose words
    url_component_count = 0
    prose_word_count = 0
    
    for token in tokens:
        # URL component indicators:
        # - Contains domain TLD: .com, .org, etc.
        # - Looks like URL path: multiple hyphens like "18-best-agile-practices"
        # - Very short (1-2 chars) or all lowercase with no vowel pattern (not a real word)
        is_url_component = (
            re.search(r'\.(com|org|net|io|dev|app|co|uk|us|edu|gov|info|biz|me)\b', token, re.IGNORECASE) or
            (len(re.findall(r'-', token)) >= 2) or  # Multiple hyphens = URL path
            (len(token) <= 2)  # Single chars or abbreviations alone aren't prose
        )
        
        if is_url_component:
            url_component_count += 1
        else:
            prose_word_count += 1
    
    # If ALL tokens are URL components (no prose words), discard
    if prose_word_count == 0 and url_component_count > 0:
        return "Content not available after cleaning web artifacts."
    
    return content


def perform_tavily_search(query: str, config, requester_name: str = None) -> Dict:
    """Perform Tavily search API call.
    
    Tavily is optimized for LLM applications and provides structured,
    citation-ready results with relevance scoring.
    
    Args:
        query: Search query string
        config: SwarmConfig instance with API credentials
        requester_name: Name of the specialist who requested the search (optional)
        
    Returns:
        Dict with keys:
        - query: str (original query)
        - answer: str (LLM-generated answer from Tavily, if available)
        - results: List[Dict] with keys: title, content, url, score
        - error: Optional[str] (error message if search failed)
    """
    if not config.tavily_search_enabled:
        return {
            "query": query,
            "answer": None,
            "results": [],
            "error": "Tavily Search API not configured. Set TAVILY_API_KEY environment variable."
        }
    
    try:
        # Import tavily client (only when needed)
        from tavily import TavilyClient
        
        # Initialize Tavily client
        tavily_client = TavilyClient(api_key=config.tavily_api_key)
        
        # Clean query before sending to Tavily: unescape HTML entities and normalize Unicode
        # Tavily expects clean plain text, not HTML-encoded strings
        clean_query = html.unescape(query)
        clean_query = normalize_unicode_punctuation(clean_query)
        
        # Show who requested the search in console output
        requester_info = f" (requested by {requester_name})" if requester_name else ""
        print(f"[SEARCH] Performing Tavily search{requester_info}: '{clean_query}'", file=sys.stderr, flush=True)
        
        # Perform search with Tavily using cleaned query
        # include_answer=True to get LLM-generated summary
        # max_results controlled by config
        response = tavily_client.search(
            query=clean_query,
            max_results=config.tavily_max_results,
            include_answer=True
        )
        
        # Extract relevant fields from Tavily response
        # Response structure: {query, answer, images, results, response_time}
        results = []
        for item in response.get("results", []):
            # Clean the content to remove markdown images and other artifacts
            raw_content = item.get("content", "No content available")
            cleaned_content = clean_search_content(raw_content)
            
            results.append({
                "title": item.get("title", ""),
                "content": cleaned_content,
                "url": item.get("url", ""),
                "score": item.get("score", 0.0)  # Tavily provides relevance scores
            })
        
        # Show results count in console
        requester_info = f" (for {requester_name})" if requester_name else ""
        print(f"[SEARCH] Tavily returned {len(results)} results{requester_info} in {response.get('response_time', 'unknown')}s\n", file=sys.stderr, flush=True)
        
        return {
            "query": clean_query,  # Return cleaned query that was actually sent
            "answer": response.get("answer", None),  # LLM-generated answer from Tavily
            "results": results,
            "error": None
        }
        
    except ImportError:
        error_msg = "Tavily Python SDK not installed. Run: pip install tavily-python"
        print(f"[SEARCH ERROR] {error_msg}", file=sys.stderr, flush=True)
        return {
            "query": query,
            "answer": None,
            "results": [],
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Tavily search failed: {str(e)}"
        print(f"[SEARCH ERROR] {error_msg}", file=sys.stderr, flush=True)
        return {
            "query": query,
            "answer": None,
            "results": [],
            "error": error_msg
        }


def read_url_with_jina(url: str, jina_api_key: Optional[str] = None, requester_name: str = None) -> Dict:
    """Fetch and extract full content from a URL using Jina AI Reader API.
    
    Jina AI Reader extracts clean, LLM-friendly markdown content from web pages,
    handling JavaScript-heavy sites and removing ads, navigation, and boilerplate.
    
    Args:
        url: The URL to fetch and read
        jina_api_key: Jina API key (optional, higher rate limits if provided)
        requester_name: Name of the specialist who requested the read (optional)
        
    Returns:
        Dict with keys:
        - url: str (original URL)
        - title: str (page title)
        - content: str (extracted markdown content)
        - description: str (meta description if available)
        - word_count: int (approximate word count)
        - error: Optional[str] (error message if read failed)
    """
    if not url.startswith(('http://', 'https://')):
        return {
            "url": url,
            "title": None,
            "content": None,
            "description": None,
            "word_count": 0,
            "error": "Invalid URL: must start with http:// or https://"
        }
    
    try:
        # Jina Reader API endpoint: prepend r.jina.ai/ to any URL
        reader_url = f"https://r.jina.ai/{url}"
        
        # Show who requested the read in console output
        requester_info = f" (requested by {requester_name})" if requester_name else ""
        print(f"[READURL] Fetching content{requester_info}: {url}", file=sys.stderr, flush=True)
        
        # Set up headers with API key if provided (for higher rate limits)
        headers = {
            "Accept": "application/json",  # Request JSON response
            "X-Return-Format": "markdown"  # Ensure markdown format
        }
        if jina_api_key:
            headers["Authorization"] = f"Bearer {jina_api_key}"
        
        # Make request to Jina Reader API with 15 second timeout
        response = requests.get(reader_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Parse JSON response
        response_json = response.json()
        
        # Jina returns: {code, status, data: {url, title, content, description, usage}, meta}
        # The actual content is nested under the "data" key
        data = response_json.get("data", {})
        
        # Extract fields from response
        title = data.get("title", "")
        content = data.get("content", "")
        description = data.get("description", "")
        
        # Clean up the markdown content
        # Remove excessive newlines (more than 2 in a row)
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        # Calculate approximate word count
        word_count = len(content.split())
        
        # Show success in console
        requester_info = f" (for {requester_name})" if requester_name else ""
        print(f"[READURL] Successfully extracted {word_count} words{requester_info} from {url}\n", file=sys.stderr, flush=True)
        
        return {
            "url": url,
            "title": title,
            "content": content,
            "description": description,
            "word_count": word_count,
            "error": None
        }
        
    except requests.exceptions.Timeout:
        error_msg = f"Request timed out after 15 seconds"
        print(f"[READURL ERROR] {error_msg} for {url}", file=sys.stderr, flush=True)
        return {
            "url": url,
            "title": None,
            "content": None,
            "description": None,
            "word_count": 0,
            "error": error_msg
        }
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error {e.response.status_code}: {e.response.reason}"
        print(f"[READURL ERROR] {error_msg} for {url}", file=sys.stderr, flush=True)
        return {
            "url": url,
            "title": None,
            "content": None,
            "description": None,
            "word_count": 0,
            "error": error_msg,
            "status_code": e.response.status_code  # Include status code for filtering
        }
    except Exception as e:
        error_msg = f"Failed to read URL: {str(e)}"
        print(f"[READURL ERROR] {error_msg} for {url}", file=sys.stderr, flush=True)
        return {
            "url": url,
            "title": None,
            "content": None,
            "description": None,
            "word_count": 0,
            "error": error_msg
        }


def escape_xml_attribute(text: str) -> str:
    """Escape text for use in double-quoted XML attributes.
    
    Only escapes characters that would break double-quoted attributes:
    - & → &amp;
    - < → &lt;
    - > → &gt;
    - " → &quot;
    
    Does NOT escape single quotes since we use double-quoted attributes.
    This produces cleaner, more readable XML output.
    
    Args:
        text: Text to escape
        
    Returns:
        XML-safe text for double-quoted attributes
    """
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def escape_xml_content(text: str) -> str:
    """Escape text for use in XML element content.
    
    Only escapes characters that would break XML structure:
    - & → &amp;
    - < → &lt;
    - > → &gt;
    
    Does NOT escape quotes since they're safe in element content.
    
    Args:
        text: Text to escape
        
    Returns:
        XML-safe text for element content
    """
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))


def format_search_results(search_data: Dict, requester_names=None) -> str:
    """Format Tavily search results in structured XML format for conversation.
    
    Tavily's 'answer' field contains an LLM-generated synthesis of all sources,
    designed specifically for fact-checking and analysis.
    
    Format: Recent search results: <results query="..." requester="@[name]"><answer>synthesis</answer><result url="..." title="...">content</result>...</results>
    
    All results are on a single line with no line breaks.
    
    **Token Optimization Strategy**:
    - NEW searches include ALL <result> tags with full URLs/titles/content
    - Specialists get ONE full phase to use the detailed results
    - After 2+ phases, cleanup_old_search_results() in agents.py trims <result> tags
    - Trimmed format keeps query + answer + ellipsis: <results query="..."><answer>...</answer>…</results>
    - This prevents duplicate searches while dramatically reducing token usage
    
    **Dual-Audience Encoding**:
    - **For LLMs (stored in messages)**: Returns XML-encoded text with entities
      (e.g., & → &amp;, < → &lt;) to ensure valid XML parsing
    - **For Humans (console display)**: main.py decodes entities via html.unescape()
      for natural readability (e.g., &amp; → &)
    - Both representations are semantically identical; encoding is for XML safety
    
    **Processing**:
    1. Decode HTML entities from Tavily (prevent double-escaping)
    2. Normalize Unicode to ASCII (smart quotes → straight quotes)
    3. Re-encode for XML safety (& → &amp;, < → &lt;, etc.)
    
    Args:
        search_data: Dict from perform_tavily_search()
        requester_names: List of specialist names who requested the search (optional), or single string for backwards compat
        
    Returns:
        XML-encoded string for message content (decoded by main.py for human display)
    """
    # Handle backwards compatibility - convert single string to list
    if isinstance(requester_names, str):
        requester_names = [requester_names]
    
    query = search_data["query"]
    answer = search_data.get("answer")
    results = search_data["results"]
    error = search_data["error"]
    
    # Normalize query to ASCII-like characters (decode HTML entities + convert Unicode punctuation)
    # This ensures the query uses plain ASCII quotes, dashes, etc. instead of fancy Unicode
    query = normalize_unicode_punctuation(html.unescape(query))
    
    # Escape query for XML attribute (used in all branches)
    escaped_query = escape_xml_attribute(query)
    
    if error:
        escaped_error = escape_xml_content(error)
        return f"Search error: {escaped_error}"
    
    if not results:
        return f"Search for '{escaped_query}' returned no results."
    
    # Build structured XML output with query, answer, and all individual results
    # NOTE: All <result> tags are included for specialists in the current phase.
    # The cleanup_old_search_results() function in agents.py will trim these
    # from prior-phase searches to save tokens while preserving query + answer.
    
    # Build individual result tags
    result_tags = []
    for result in results:
        content = result.get("content", "")
        url = result.get("url", "")
        title = result.get("title", "")
        
        # Normalize content, URL, and title to ASCII-like characters
        content = normalize_unicode_punctuation(html.unescape(content))
        url = normalize_unicode_punctuation(html.unescape(url))
        title = normalize_unicode_punctuation(html.unescape(title))
        
        # Escape for XML: content is element content, url and title are attributes
        escaped_content = escape_xml_content(content)
        escaped_url = escape_xml_attribute(url)
        escaped_title = escape_xml_attribute(title)
        
        result_tags.append(f'<result url="{escaped_url}" title="{escaped_title}">{escaped_content}</result>')
    
    # Build results XML with answer as a child element (not attribute)
    # Normalize answer field if present
    answer_tag = ""
    if answer:
        answer = normalize_unicode_punctuation(html.unescape(answer))
        escaped_answer = escape_xml_content(answer)  # Element content: no quote escaping
        answer_tag = f'<answer>{escaped_answer}</answer>'
    
    # Build results tag with query and optional requester attribute
    # Format: <results query="..." requester="@[Name1] @[Name2]"><answer>...</answer><result>...</result>...</results>
    if requester_names:
        # Normalize and format all requester names (space-separated)
        formatted_requesters = []
        for name in requester_names:
            name_normalized = normalize_unicode_punctuation(name)
            formatted_requesters.append(f"@[{name_normalized}]")
        escaped_requester = escape_xml_attribute(" ".join(formatted_requesters))
        results_xml = f'<results query="{escaped_query}" requester="{escaped_requester}">{answer_tag}{"".join(result_tags)}</results>'
    else:
        results_xml = f'<results query="{escaped_query}">{answer_tag}{"".join(result_tags)}</results>'
    
    # Return entire message on one line with XML results
    return f"Recent search results: {results_xml}"


def format_readurl_results(url_data: Dict, requester_names=None) -> str:
    """Format Jina ReadURL results in structured XML format for conversation.
    
    Format: URL content: <content url="..." title="..." requester="@[Name1] @[Name2]">markdown content</content>
    
    The markdown content is in a single <content> element with all metadata as attributes,
    making it self-contained. Newlines within the content are preserved.
    
    Args:
        url_data: Dict from read_url_with_jina() with keys: url, title, content, description, error
        requester_names: List of specialist names who requested the read (optional), or single string for backwards compat
        
    Returns:
        Formatted string with URL content or error message
    """
    # Handle backwards compatibility - convert single string to list
    if isinstance(requester_names, str):
        requester_names = [requester_names]
    
    url = url_data.get("url", "")
    
    # Check for errors first
    if url_data.get("error"):
        error_msg = url_data["error"]
        status_code = url_data.get("status_code")
        escaped_error = escape_xml_attribute(error_msg)
        escaped_url = escape_xml_attribute(url)
        
        # Build base attributes
        base_attrs = f'url="{escaped_url}"'
        
        # Add requester if provided
        if requester_names:
            formatted_requesters = []
            for name in requester_names:
                name_normalized = normalize_unicode_punctuation(name)
                formatted_requesters.append(f"@[{name_normalized}]")
            escaped_requester = escape_xml_attribute(" ".join(formatted_requesters))
            base_attrs += f' requester="{escaped_requester}"'
        
        # For HTTP status codes (2xx, 3xx, 4xx, 5xx), add response-status attribute
        if status_code is not None:
            base_attrs += f' response-status="{status_code}"'
        
        # Add error message
        base_attrs += f' error="{escaped_error}"'
        
        return f'URL read failed: <content {base_attrs}></content>'
    
    # Extract fields
    title = url_data.get("title", "")
    markdown_content = url_data.get("content", "")
    description = url_data.get("description", "")
    
    # Escape for XML
    escaped_url = escape_xml_attribute(url)
    escaped_title = escape_xml_attribute(title)
    escaped_content = escape_xml_content(markdown_content)  # Preserve newlines in content
    
    # Build single <content> tag with all metadata as attributes
    # Format: <content url="..." title="..." requester="@[Name1] @[Name2]">markdown</content>
    attrs = [
        f'url="{escaped_url}"',
        f'title="{escaped_title}"'
    ]
    
    # Add optional attributes
    if description:
        escaped_desc = escape_xml_attribute(description)
        attrs.append(f'description="{escaped_desc}"')
    
    if requester_names:
        # Format multiple requesters space-separated
        formatted_requesters = []
        for name in requester_names:
            name_normalized = normalize_unicode_punctuation(name)
            formatted_requesters.append(f"@[{name_normalized}]")
        escaped_requester = escape_xml_attribute(" ".join(formatted_requesters))
        attrs.append(f'requester="{escaped_requester}"')
    
    content_tag = f'<content {" ".join(attrs)}>{escaped_content}</content>'
    
    # Return entire message with XML content
    return f"URL content: {content_tag}"


def process_search_requests(message_content: str, config, current_phase: int, requester_name: str = None) -> List[AIMessage]:
    """Detect and process ALL search requests in a message using Tavily.
    
    Each @[Search][query] generates its own separate Notice message.
    Multiple searches in one message are NOT combined - each is evaluated independently.
    
    Args:
        message_content: Specialist's message content
        config: SwarmConfig instance
        current_phase: Current phase number for search result messages
        requester_name: Name of the specialist who requested the search (optional)
        
    Returns:
        List of AIMessage objects with search results (one AIMessage per query found)
    """
    search_queries = detect_search_requests(message_content)
    
    if not search_queries:
        return []
    
    if not config.tavily_search_enabled:
        # Return single message explaining search is not configured
        timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
        return [
            AIMessage(
                content="Tavily Search API not configured. To enable search, set TAVILY_API_KEY environment variable. Get your API key at: https://tavily.com",
                name="Search tool",
                additional_kwargs={"phase": current_phase, "timestamp": timestamp}
            )
        ]
    
    # Perform searches and create messages
    search_messages = []
    for query in search_queries:
        search_data = perform_tavily_search(query, config, requester_name)
        formatted_results = format_search_results(search_data, requester_name)
        
        # Create search message with phase metadata (with timezone)
        timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
        search_message = AIMessage(
            content=formatted_results,
            name="Search tool",
            additional_kwargs={"phase": current_phase, "timestamp": timestamp}
        )
        search_messages.append(search_message)
    
    return search_messages


def process_readurl_requests(message_content: str, jina_api_key: Optional[str], current_phase: int, requester_name: str = None) -> List[AIMessage]:
    """Detect and process ALL ReadURL requests in a message using Jina AI Reader.
    
    Each @[ReadURL][url] generates its own separate message with full page content.
    
    Args:
        message_content: Specialist's message content
        jina_api_key: Jina API key for higher rate limits (optional, from JINA_API_KEY env var)
        current_phase: Current phase number for URL read result messages
        requester_name: Name of the specialist who requested the read (optional)
        
    Returns:
        List of AIMessage objects with URL content (one AIMessage per URL found)
    """
    urls = detect_readurl_requests(message_content)
    
    if not urls:
        return []
    
    # Perform URL reads and create messages
    readurl_messages = []
    for url in urls:
        url_data = read_url_with_jina(url, jina_api_key, requester_name)
        formatted_content = format_readurl_results(url_data, requester_name)
        
        # Create ReadURL message with phase metadata (with timezone)
        timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
        readurl_message = AIMessage(
            content=formatted_content,
            name="ReadURL tool",
            additional_kwargs={"phase": current_phase, "timestamp": timestamp}
        )
        readurl_messages.append(readurl_message)
    
    return readurl_messages
