# Fetch MCP Server

**Purpose**: Fetch URLs and extract content from web pages with built-in HTML to markdown conversion

## Triggers
- URL fetching requests: "fetch this URL", "get content from website"
- Web scraping needs for documentation or research
- Need to retrieve and process web content programmatically
- Cross-domain content retrieval requirements
- API endpoint testing and response inspection

## Choose When
- **Over WebSearch**: When you need the actual page content, not search results
- **Over native fetch**: When you need HTML-to-markdown conversion
- **For web scraping**: Extract structured content from websites
- **For API testing**: Retrieve and inspect API responses
- **For documentation**: Fetch online documentation and tutorials

## Works Best With
- **Sequential**: Fetch provides content → Sequential analyzes and structures
- **Filesystem**: Fetch retrieves → Filesystem saves locally for processing

## Examples
```
"fetch content from example.com" → Fetch (retrieve and convert webpage)
"get the latest React documentation" → Fetch (scrape official docs)
"check API endpoint response" → Fetch (test and inspect API)
"download tutorial content" → Fetch (retrieve learning materials)
"search for React hooks" → WebSearch (find relevant pages first)
```

## Key Features
- Automatic HTML to markdown conversion
- Handles redirects and authentication
- Supports custom headers and parameters
- Extracts meaningful content from complex pages
- Rate limiting and timeout handling
