# Tavily Search Setup Guide

This guide explains how to configure Tavily Search for the Axion Swarm multi-agent system.

## What is Tavily?

Tavily is a search API specifically designed for Large Language Model (LLM) applications. Unlike traditional search APIs, Tavily provides:

- **LLM-Optimized Results**: Content is structured and formatted specifically for AI agents
- **Relevance Scoring**: Each result includes a relevance score for the query
- **Citation-Ready**: Direct URLs to sources for fact-checking
- **Multi-Source Aggregation**: Aggregates content from 20+ trusted sources per query
- **Quick Summaries**: Optional LLM-generated answer to the query
- **Real-Time Data**: Access to current, up-to-date information

Learn more: https://docs.tavily.com

## Setup Steps

### 1. Get Your Tavily API Key

1. Visit [https://tavily.com](https://tavily.com)
2. Sign up for a free account
3. Navigate to your dashboard to find your API key
4. Copy your API key from the Tavily Dashboard (format: `tvly-prod-xxxxxxxxxxxxxxxxxxxxxxx` for production keys)

### 2. Configure Environment Variables

Add your Tavily API key to your environment:

```bash
export TAVILY_API_KEY="tvly-prod-[your-api-key-from-tavily-dashboard]"
```

**Optional Configuration:**

```bash
# Maximum number of search results per query (default: 5, max: 20)
export TAVILY_MAX_RESULTS=5
```

### 3. Install Tavily Python SDK

```bash
pip install tavily-python
```

### 4. Verify Configuration

The system will automatically detect your Tavily API key. If configured correctly, specialists can use the `@[Search][query]` syntax in their responses.

## Usage in Axion Swarm

### For Specialists

Any specialist can perform searches using this syntax:

```
@[Search][your search query here]
```

**Examples:**
- `@[Search][topic X new features 2025]`
- `@[Search][service Y pricing 2025]`
- `@[Search][domain Z best practices 2024-2025]`

### Search Results Format

Search results appear as "Search tool:" messages and include:

1. **Quick Summary**: LLM-generated answer to the query (optional)
2. **Source Count**: Number of relevant sources found
3. **For Each Source**:
   - Title and relevance score (0-100%)
   - Content: LLM-optimized snippet from the source
   - Source: Direct URL for citation

### Research Specialist Role

The Research specialist has specific fact-checking responsibilities:
- Proactively use `@[Search]` to verify statements from other specialists
- Focus on verifying best practices and current information
- When search results conflict with specialist statements, @mention them with the conflicting information

## Rate Limits & Pricing

- **Free Tier**: Check Tavily's current free tier limits at https://tavily.com/pricing
- **Rate Limits**: Tavily provides different rate limits for development and production
- **API Credits**: Some search modes (like `advanced` search depth) use more credits

See: https://docs.tavily.com/documentation/api-reference/credits-pricing

## Troubleshooting

### "Tavily Search API not configured"

**Solution**: Ensure `TAVILY_API_KEY` environment variable is set.

### "Tavily Python SDK not installed"

**Solution**: Run `pip install tavily-python`

### "Tavily search failed: ..."

**Possible causes:**
- Invalid API key
- Rate limit exceeded
- Network connectivity issues
- API service temporarily unavailable

Check the error message in stderr for specific details.

## API Documentation

Full Tavily API documentation: https://docs.tavily.com/documentation/api-reference/endpoint/search

Key features:
- **Search Depth**: `basic` (1 credit) vs `advanced` (2 credits)
- **Topic Filtering**: `general`, `news`, `finance`
- **Time Range**: Filter by recent days/weeks/months
- **Domain Control**: Include or exclude specific domains
- **Country Boost**: Prioritize results from specific countries

## Security Notes

- Keep your `TAVILY_API_KEY` secure and never commit it to version control
- Use environment variables or secure secret management systems
- Rotate your API key if compromised
- Monitor your API usage through Tavily's dashboard

## Support

- Tavily Documentation: https://docs.tavily.com
- Support: Available through Tavily's platform
- Community: Join Tavily's community for updates and best practices

