#!/usr/bin/env node
// Zero-dependency MCP stdio server wrapping the Apify "Fast Reddit Scraper"
// (practicaltools/apify-reddit-api). Reads APIFY_TOKEN from env.
// Exposes one tool: reddit_search. Reads Reddit without Reddit API creds and
// bypasses Reddit's bot block (Apify runs the fetch on its own infra).
//
// Deployed to the Bifrost container at /app/data/reddit-apify.js (the ./data
// volume) and registered as a stdio MCP client named "RedditApify" with
// command=node, args=[/app/data/reddit-apify.js], envs=[APIFY_TOKEN,PATH,HOME].
// See README.md in this folder.

const ACTOR = "practicaltools~apify-reddit-api";

const TOOL = {
  name: "reddit_search",
  description:
    "Search Reddit for posts via Apify (no Reddit API credentials needed; bypasses Reddit's bot block). " +
    "Returns title, subreddit, url, body excerpt, upvotes, and comment count. Use for community sentiment / research.",
  inputSchema: {
    type: "object",
    properties: {
      query: { type: "string", description: "Search query / topic." },
      subreddits: {
        type: "array", items: { type: "string" },
        description: "Optional subreddit names (without r/) to seed the crawl.",
      },
      limit: { type: "integer", description: "Max posts to return (default 15)." },
      sort: { type: "string", enum: ["relevance", "hot", "top", "new", "comments"], description: "Default relevance." },
      time: { type: "string", enum: ["hour", "day", "week", "month", "year", "all"], description: "Default all." },
    },
    required: ["query"],
  },
};

function send(msg) { process.stdout.write(JSON.stringify(msg) + "\n"); }

async function runSearch(args) {
  const token = process.env.APIFY_TOKEN;
  if (!token) return { content: [{ type: "text", text: "Error: APIFY_TOKEN not set." }], isError: true };
  const input = {
    searches: [args.query],
    searchPosts: true, searchComments: false, searchCommunities: false, searchUsers: false,
    skipComments: true, skipUserPosts: true, skipCommunity: true,
    sort: args.sort || "relevance", time: args.time || "all",
    maxItems: args.limit || 15,
  };
  if (Array.isArray(args.subreddits) && args.subreddits.length) {
    input.startUrls = args.subreddits.map((s) => ({
      url: "https://www.reddit.com/r/" + String(s).replace(/^r\//, "").trim() + "/",
    }));
  }
  const u = "https://api.apify.com/v2/acts/" + ACTOR + "/run-sync-get-dataset-items?token=" + token;
  try {
    const r = await fetch(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) });
    const t = await r.text();
    let arr; try { arr = JSON.parse(t); } catch (e) { return { content: [{ type: "text", text: "Apify error " + r.status + ": " + t.slice(0, 300) }], isError: true }; }
    if (!Array.isArray(arr)) return { content: [{ type: "text", text: "Apify non-array (status " + r.status + "): " + t.slice(0, 300) }], isError: true };
    const blocks = arr.map((it, i) => {
      const sub = it.parsedCommunityName || it.communityName || "?";
      const title = it.title || "(no title)";
      const body = String(it.body || "").replace(/\s+/g, " ").slice(0, 500);
      return `[${i + 1}] r/${sub} | ▲${it.upVotes || 0} | ${it.numberOfComments || 0} comments\n${title}\n${it.url || ""}\n${body}`;
    });
    return { content: [{ type: "text", text: blocks.join("\n\n") || "No results." }] };
  } catch (e) {
    return { content: [{ type: "text", text: "Request failed: " + String(e).slice(0, 200) }], isError: true };
  }
}

async function handle(msg) {
  const { id, method, params } = msg;
  if (method === "initialize") {
    send({ jsonrpc: "2.0", id, result: {
      protocolVersion: (params && params.protocolVersion) || "2024-11-05",
      capabilities: { tools: {} },
      serverInfo: { name: "reddit-apify", version: "1.0.0" },
    }});
  } else if (method === "tools/list") {
    send({ jsonrpc: "2.0", id, result: { tools: [TOOL] } });
  } else if (method === "tools/call") {
    if (!params || params.name !== TOOL.name) {
      send({ jsonrpc: "2.0", id, error: { code: -32602, message: "Unknown tool" } });
      return;
    }
    send({ jsonrpc: "2.0", id, result: await runSearch(params.arguments || {}) });
  } else if (method === "ping") {
    send({ jsonrpc: "2.0", id, result: {} });
  } else if (method && method.startsWith("notifications/")) {
    // notifications: no response
  } else if (id !== undefined) {
    send({ jsonrpc: "2.0", id, error: { code: -32601, message: "Method not found: " + method } });
  }
}

let buf = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  buf += chunk;
  let i;
  while ((i = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, i).trim();
    buf = buf.slice(i + 1);
    if (line) { try { handle(JSON.parse(line)); } catch (e) {} }
  }
});
process.stdin.on("end", () => process.exit(0));
