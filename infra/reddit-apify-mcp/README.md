# reddit-apify MCP server

A zero-dependency MCP stdio server that exposes a `reddit_search` tool backed by
the Apify **Fast Reddit Scraper** (`practicaltools/apify-reddit-api`). It reads
Reddit **without Reddit API credentials** and bypasses Reddit's 2026 bot block
(Apify runs the fetch on its own residential-proxy infrastructure).

Cost: ~$2 / 1,000 results, comfortably inside Apify's free $5/month credit for
light personal use.

## Why this exists

Reddit ended self-service API keys (Nov 2025) and now blocks unauthenticated /
scraped access at the network level — proven dead from our own IP via direct
fetch (403), Firecrawl stealth (anti-bot), Redlib mirrors (Anubis challenge), and
Scrapling (timeout). Apify was the only working $0 path. The official Reddit API
application is also pending (`docs/reddit-api-application.md`); if approved, swap
this tool's backend for the official API.

## Deploy (Bifrost on the Mac Mini, Docker)

1. Copy `reddit-apify.js` into Bifrost's data volume:
   `~/bifrost/data/reddit-apify.js`  → in-container `/app/data/reddit-apify.js`
2. Add the token to `~/bifrost/.env`:
   `APIFY_TOKEN=apify_api_...`
3. Recreate the container so it loads the env:
   `cd ~/bifrost && docker compose up -d --force-recreate`
4. Register the MCP client via the Bifrost API (POST `/api/mcp/client`):
   ```json
   {
     "name": "RedditApify",
     "is_code_mode_client": false,
     "connection_type": "stdio",
     "connection_string": { "value": "", "env_var": "", "from_env": false },
     "stdio_config": { "command": "node", "args": ["/app/data/reddit-apify.js"], "envs": ["APIFY_TOKEN", "PATH", "HOME"] },
     "auth_type": "none",
     "tools_to_execute": ["*"],
     "is_ping_available": true,
     "tool_sync_interval": 10,
     "disabled": false,
     "allow_on_all_virtual_keys": false
   }
   ```
   Note: `tool_sync_interval` is in **minutes** on input (Bifrost re-scales to ns).

The tool `reddit_search` then appears in new Bifrost sessions. The `deep-research`
skill's tool map points at it for Reddit sentiment.

## Tool

`reddit_search(query, [subreddits], [limit=15], [sort=relevance], [time=all])`
→ returns posts with title, subreddit, url, body excerpt, upvotes, comment count.
