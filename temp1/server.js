const express = require("express");
const path = require("path");
const compression = require("compression");
const fs = require("fs");
const session = require("express-session");
const OAuth = require("oauth-1.0a");
const crypto = require("crypto");
const { GoogleAuth } = require("google-auth-library");
require("dotenv").config();

const auth = new GoogleAuth({
  scopes: "https://www.googleapis.com/auth/cloud-platform"
});

// Redirect console logs to a local file for diagnosis
const logFile = path.join(__dirname, "server.log");
const logStream = fs.createWriteStream(logFile, { flags: "a" });
const originalLog = console.log;
const originalError = console.error;

console.log = (...args) => {
  const formatted = args.map(a => a instanceof Error ? a.stack || a.message : (typeof a === 'object' ? JSON.stringify(a) : a)).join(" ");
  logStream.write(`[LOG] ${new Date().toISOString()} - ${formatted}\n`);
  originalLog.apply(console, args);
};

console.error = (...args) => {
  const formatted = args.map(a => a instanceof Error ? a.stack || a.message : (typeof a === 'object' ? JSON.stringify(a) : a)).join(" ");
  logStream.write(`[ERROR] ${new Date().toISOString()} - ${formatted}\n`);
  originalError.apply(console, args);
};

const app = express();
app.use(compression({
  // gzip buffers writes internally to build an efficient compression window
  // and only flushes to the network once enough data accumulates or the
  // response ends -- that silently turns /api/geap/query's SSE stream back
  // into a one-shot response even though the server writes deltas as they
  // arrive. Exclude it from compression entirely; SSE frames are small and
  // frequent, so there's no real compression win to trade away here.
  filter: (req, res) => {
    if (req.path === "/api/geap/query") return false;
    return compression.filter(req, res);
  }
}));
app.use(express.json());

app.use(
  session({
    secret: process.env.SESSION_SECRET || "etrade_poc_local_secret_12345",
    resave: false,
    saveUninitialized: true,
    cookie: { secure: false }
  })
);

// Log session state on every incoming request
app.use((req, res, next) => {
  console.log(`[REQUEST] ${req.method} ${req.url} - sessionID: ${req.sessionID} - sessionKeys: ${Object.keys(req.session || {})}`);
  next();
});

// Disable browser caching for all E*TRADE API and Auth endpoints
app.use(["/api", "/auth"], (req, res, next) => {
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate");
  res.setHeader("Pragma", "no-cache");
  res.setHeader("Expires", "0");
  res.setHeader("Surrogate-Control", "no-store");
  next();
});

// Startup CSS Minification
const cssDir = path.join(__dirname, "public", "css");
if (fs.existsSync(cssDir)) {
  const cssFiles = fs.readdirSync(cssDir).filter(f => f.endsWith(".css") && !f.endsWith(".min.css"));
  cssFiles.forEach(file => {
    const fullPath = path.join(cssDir, file);
    try {
      const content = fs.readFileSync(fullPath, "utf8");
      const minified = content
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .replace(/\s+/g, " ")
        .replace(/\s*([\{\}:;\,])\s*/g, "$1")
        .replace(/;\}/g, "}")
        .trim();
      const minFile = file.replace(/\.css$/, ".min.css");
      fs.writeFileSync(path.join(cssDir, minFile), minified, "utf8");
    } catch (err) {
      console.error(`Error minifying CSS file ${file}:`, err);
    }
  });
}

const port = Number(process.env.PORT || 3000);
const publicDir = path.join(__dirname, "public");

app.disable("x-powered-by");

app.use(
  express.static(publicDir, {
    extensions: ["html"],
    maxAge: process.env.NODE_ENV === "production" ? "1h" : 0,
    etag: true
  })
);

const appRoutes = [
  "/",
  "/accounts",
  "/accounts/portfolios",
  "/accounts/watch-lists",
  "/accounts/orders",
  "/accounts/balances",
  "/accounts/activity",
  "/accounts/banking",
  "/accounts/tax-center",
  "/accounts/documents",
  "/accounts/dividend-reinvestment",
  "/accounts/open-account",
  "/pay-transfer",
  "/trading",
  "/markets-ideas",
  "/at-work",
  "/planning",
  "/what-we-offer",
  "/support",
  "/alerts",
  "/documents",
  "/profile",
  "/search",
  "/agent-studio",
  "/agent-fabric",
  "/ai-insights"
];

app.get("/api/search", async (req, res) => {
  const query = req.query.q || "";
  const domainsStr = req.query.domains || "";
  if (!query) {
    return res.json([]);
  }

  try {
    let searchQuery = query;
    if (domainsStr) {
      const domains = domainsStr.split(",").map(d => `site:${d.trim()}`);
      if (domains.length > 0) {
        searchQuery += ` (${domains.join(" OR ")})`;
      }
    }

    const url = `https://news.google.com/rss/search?q=${encodeURIComponent(searchQuery)}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Google News returned status ${response.status}`);
    }
    const xmlText = await response.text();

    const items = [];
    const itemRegex = /<item>([\s\S]*?)<\/item>/g;
    let match;
    
    function decodeHtmlEntities(str) {
      return str
        .replace(/&amp;/g, "&")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/&apos;/g, "'");
    }

    while ((match = itemRegex.exec(xmlText)) !== null) {
      const content = match[1];
      const titleMatch = content.match(/<title>([\s\S]*?)<\/title>/);
      const linkMatch = content.match(/<link>([\s\S]*?)<\/link>/);
      const pubDateMatch = content.match(/<pubDate>([\s\S]*?)<\/pubDate>/);
      const sourceMatch = content.match(/<source[^>]*>([\s\S]*?)<\/source>/);
      
      const title = titleMatch ? decodeHtmlEntities(titleMatch[1]) : "";
      const link = linkMatch ? linkMatch[1] : "";
      const pubDate = pubDateMatch ? pubDateMatch[1] : "";
      const source = sourceMatch ? decodeHtmlEntities(sourceMatch[1]) : "";

      let normalizedSource = source;
      if (source.toLowerCase().includes("yahoo")) normalizedSource = "Yahoo Finance";
      else if (source.toLowerCase().includes("bloomberg")) normalizedSource = "Bloomberg";
      else if (source.toLowerCase().includes("reuters")) normalizedSource = "Reuters";
      else if (source.toLowerCase().includes("morningstar")) normalizedSource = "Morningstar";

      items.push({
        title,
        content: `Link: ${link}\nPublished: ${pubDate}\n[Source: ${normalizedSource}]`,
        source: source.toLowerCase()
      });
    }

    // Return top 5 live articles
    res.json(items.slice(0, 5));
  } catch (error) {
    console.error("Error fetching live search:", error);
    res.status(500).json({ error: error.message });
  }
});

// ── E*TRADE OAuth Handshake and Proxy Endpoints ──

function getOAuthHelper() {
  return OAuth({
    consumer: {
      key: process.env.ETRADE_CONSUMER_KEY || "",
      secret: process.env.ETRADE_CONSUMER_SECRET || ""
    },
    signature_method: "HMAC-SHA1",
    hash_function(base_string, key) {
      return crypto.createHmac("sha1", key).update(base_string).digest("base64");
    }
  });
}

async function queryEtrade(req, urlPath, queryParams = {}) {
  const ETRADE_HOST = process.env.ETRADE_ENV === "production" ? "https://api.etrade.com" : "https://apisb.etrade.com";
  const token = {
    key: req.session.accessToken,
    secret: req.session.accessTokenSecret
  };

  if (!token.key || !token.secret) {
    throw new Error("E*TRADE Session not connected. Please log in.");
  }

  const queryString = Object.keys(queryParams).length > 0
    ? "?" + new URLSearchParams(queryParams).toString()
    : "";

  const request_data = {
    url: `${ETRADE_HOST}${urlPath}${queryString}`,
    method: "GET"
  };

  const oauthHelper = getOAuthHelper();
  const authHeader = oauthHelper.toHeader(oauthHelper.authorize(request_data, token));

  const response = await fetch(request_data.url, {
    method: request_data.method,
    headers: {
      ...authHeader,
      "Accept": "application/json"
    }
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`E*TRADE API Error ${response.status}: ${errText}`);
  }

  return await response.json();
}

app.get("/auth/etrade", async (req, res) => {
  console.log("Initiating OAuth login: sessionID =", req.sessionID);
  const ETRADE_HOST = process.env.ETRADE_ENV === "production" ? "https://api.etrade.com" : "https://apisb.etrade.com";
  const key = process.env.ETRADE_CONSUMER_KEY || "";
  const secret = process.env.ETRADE_CONSUMER_SECRET || "";

  if (!key || !secret) {
    return res.status(400).send("E*TRADE Consumer Key and Secret are not configured in your .env file.");
  }

  const request_data = {
    url: `${ETRADE_HOST}/oauth/request_token`,
    method: "POST",
    data: { oauth_callback: "oob" } // Out-Of-Band PIN workflow
  };

  try {
    const oauthHelper = getOAuthHelper();
    const authHeader = oauthHelper.toHeader(oauthHelper.authorize(request_data));
    
    const response = await fetch(request_data.url, {
      method: request_data.method,
      headers: { ...authHeader }
    });
    
    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Request Token Error: ${response.status} - ${errText}`);
    }

    const text = await response.text();
    const params = new URLSearchParams(text);
    req.session.requestToken = params.get("oauth_token");
    req.session.requestTokenSecret = params.get("oauth_token_secret");

    const loginUrl = `https://us.etrade.com/e/t/etws/authorize?key=${key}&token=${req.session.requestToken}`;
    res.redirect(loginUrl);
  } catch (err) {
    console.error("OAuth request token error:", err);
    res.status(500).send(`Authentication failed: ${err.message}`);
  }
});

app.get("/auth/etrade/callback", async (req, res) => {
  console.log("OAuth callback hit: sessionID =", req.sessionID, "pin =", req.query.pin);
  const ETRADE_HOST = process.env.ETRADE_ENV === "production" ? "https://api.etrade.com" : "https://apisb.etrade.com";
  const verifier = req.query.pin || req.query.oauth_verifier;

  if (!verifier) {
    return res.status(400).send("Missing verification PIN. Please supply 'pin' query parameter.");
  }

  if (!req.session.requestToken || !req.session.requestTokenSecret) {
    return res.status(400).send("Missing request tokens in session. Please start authentication from /auth/etrade.");
  }

  const request_data = {
    url: `${ETRADE_HOST}/oauth/access_token`,
    method: "POST",
    data: { oauth_verifier: verifier }
  };

  const token = {
    key: req.session.requestToken,
    secret: req.session.requestTokenSecret
  };

  try {
    const oauthHelper = getOAuthHelper();
    const authHeader = oauthHelper.toHeader(oauthHelper.authorize(request_data, token));
    
    const response = await fetch(request_data.url, {
      method: request_data.method,
      headers: { ...authHeader }
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Access Token Error: ${response.status} - ${errText}`);
    }

    const text = await response.text();
    const params = new URLSearchParams(text);
    req.session.accessToken = params.get("oauth_token");
    req.session.accessTokenSecret = params.get("oauth_token_secret");
    req.session.etradeConnected = true;

    req.session.save((saveErr) => {
      if (saveErr) {
        console.error("Failed to save session during login callback:", saveErr);
      }
      res.send(`
        <script>
          alert("SUCCESS: Connected to E*TRADE Sandbox!");
          if (window.opener) {
            window.opener.location.reload();
            window.close();
          } else {
            window.location.href = "/";
          }
        </script>
      `);
    });
  } catch (err) {
    console.error("OAuth access token error:", err);
    res.status(500).send(`OAuth verification failed: ${err.message}`);
  }
});

app.get("/api/etrade/status", (req, res) => {
  console.log("Status query: connected =", !!req.session.etradeConnected, "sessionID =", req.sessionID);
  res.json({
    connected: !!req.session.etradeConnected,
    env: process.env.ETRADE_ENV || "sandbox"
  });
});

app.get("/api/etrade/disconnect", (req, res) => {
  req.session.accessToken = null;
  req.session.accessTokenSecret = null;
  req.session.etradeConnected = false;
  req.session.save((saveErr) => {
    if (saveErr) {
      console.error("Failed to save session during disconnect:", saveErr);
    }
    res.json({ success: true });
  });
});

app.get("/api/etrade/accounts", async (req, res) => {
  try {
    const data = await queryEtrade(req, "/v1/accounts/list.json");
    res.json(data);
  } catch (err) {
    console.error("Error fetching /api/etrade/accounts:", err);
    res.status(500).json({ error: err.message });
  }
});

app.get("/api/etrade/portfolio/:accountIdKey", async (req, res) => {
  try {
    const data = await queryEtrade(req, `/v1/accounts/${req.params.accountIdKey}/portfolio.json`);
    res.json(data);
  } catch (err) {
    console.error(`Error fetching portfolio for ${req.params.accountIdKey}:`, err);
    res.status(500).json({ error: err.message });
  }
});

app.get("/api/etrade/balances/:accountIdKey", async (req, res) => {
  try {
    const data = await queryEtrade(req, `/v1/accounts/${req.params.accountIdKey}/balance.json`, { instType: "BROKERAGE" });
    res.json(data);
  } catch (err) {
    console.error(`Error fetching balances for ${req.params.accountIdKey}:`, err);
    res.status(500).json({ error: err.message });
  }
});

app.get("/api/etrade/transactions/:accountIdKey", async (req, res) => {
  try {
    const data = await queryEtrade(req, `/v1/accounts/${req.params.accountIdKey}/transactions.json`);
    res.json(data);
  } catch (err) {
    console.error(`Error fetching transactions for ${req.params.accountIdKey}:`, err);
    res.status(500).json({ error: err.message });
  }
});

// Reasoning Engine (Agent Engine) resource identifying the deployed GEAP agent.
// Override via env vars for other targets; these defaults match the current deployment.
const GEAP_ENGINE_PROJECT = process.env.GEAP_ENGINE_PROJECT || "labs-gcp-msls-16495-1782829337";
const GEAP_ENGINE_LOCATION = process.env.GEAP_ENGINE_LOCATION || "us-east1";
const GEAP_ENGINE_ID = process.env.GEAP_ENGINE_ID || "3178503397946949632";

// The ADK AdkApp wrapper only registers "stream_query" / "async_stream_query" for
// actually running the agent (see register_operations() in the ADK SDK) -- there is
// no plain "query" class_method. Running the agent therefore requires the
// `:streamQuery` REST method, whose response body is a sequence of concatenated
// JSON event objects (not a single JSON document, and not always newline-delimited).
//
// This tracks brace-depth/string-escaping state across successive feed() calls
// so events can be extracted as soon as they arrive over the wire, instead of
// waiting for the whole (potentially long) response body to finish.
function createIncrementalGeapEventParser() {
  let buffer = "";
  let pos = 0;
  let depth = 0;
  let start = -1;
  let inString = false;
  let escapeNext = false;

  function feed(chunkText) {
    buffer += chunkText;
    const events = [];

    while (pos < buffer.length) {
      const ch = buffer[pos];

      if (start === -1) {
        if (ch === "{") {
          start = pos;
          depth = 1;
        }
        pos++;
        continue;
      }

      if (escapeNext) {
        escapeNext = false;
        pos++;
        continue;
      }
      if (ch === "\\") {
        escapeNext = true;
        pos++;
        continue;
      }
      if (ch === '"') {
        inString = !inString;
        pos++;
        continue;
      }
      if (inString) {
        pos++;
        continue;
      }

      if (ch === "{") {
        depth++;
      } else if (ch === "}") {
        depth--;
        if (depth === 0) {
          const raw = buffer.slice(start, pos + 1);
          try {
            events.push(JSON.parse(raw));
          } catch (err) {
            console.error("[GEAP] Failed to parse event chunk:", err.message);
          }
          start = -1;
        }
      }
      pos++;
    }

    // Trim the consumed prefix so the buffer doesn't grow unbounded across a long stream.
    const keepFrom = start === -1 ? pos : start;
    buffer = buffer.slice(keepFrom);
    pos -= keepFrom;
    if (start !== -1) start -= keepFrom;

    return events;
  }

  return { feed };
}

// One-shot convenience wrapper for callers that already have the complete raw
// response text (e.g. the small, non-streamed session-creation call).
function parseGeapStreamEvents(rawText) {
  return createIncrementalGeapEventParser().feed(rawText);
}

// Reconstructs the agent's final reply from the event stream, skipping partial
// (in-progress) chunks and the echoed user message.
function extractGeapText(events) {
  const chunks = [];
  for (const event of events) {
    if (event.partial) continue;
    if (event.author === "user") continue;
    const parts = event.content?.parts;
    if (!parts) continue;
    const text = parts
      .map((part) => part.text)
      .filter((t) => typeof t === "string" && t.length > 0)
      .join("");
    if (text) chunks.push(text);
  }
  return chunks.join("\n\n").trim();
}

// Maps ADK tool names a sub-agent can call to the exact [[WIDGET:X]] sentinel
// chat.js's addMessageToUI() already knows how to splice into the rendered
// message. The tool itself carries no data -- the client builds the widget
// from its own local state -- so this is purely a "show widget X now" flag.
const WIDGET_SIGNAL_TOOLS = {
  show_rebalance_widget: "REBALANCE_FORM"
};

// Scans the same event stream extractGeapText() reads for a widget-signal
// tool call. Returns the matching sentinel, or "" if the agent didn't call one.
function extractWidgetSignal(events) {
  for (const event of events) {
    for (const part of event.content?.parts || []) {
      const toolName = part.functionCall?.name;
      if (toolName && WIDGET_SIGNAL_TOOLS[toolName]) {
        return `[[WIDGET:${WIDGET_SIGNAL_TOOLS[toolName]}]]`;
      }
    }
  }
  return "";
}

// Tools whose *return value* (not just the call, unlike WIDGET_SIGNAL_TOOLS)
// carries the actual UI payload: an A2UI envelope built server-side by
// app/a2ui/envelope.py (geap-agent), already validated against the A2UI
// catalog before the tool ever returned it. See docs/A2UI.md.
const A2UI_SIGNAL_TOOLS = new Set(["render_retirement_dashboard"]);

// Scans the event stream for a functionResponse from an A2UI signal tool and
// returns its `a2ui` envelope, or null if the agent didn't call one this turn.
function extractA2uiPayload(events) {
  for (const event of events) {
    for (const part of event.content?.parts || []) {
      const fr = part.functionResponse;
      if (fr && A2UI_SIGNAL_TOOLS.has(fr.name) && fr.response && fr.response.a2ui) {
        return fr.response.a2ui;
      }
    }
  }
  return null;
}

// Decides which text deltas to forward to the browser as each event arrives,
// so the client can render progressively instead of waiting for the whole
// turn to finish. Partial events are incremental streaming deltas (same
// semantics as the underlying Gemini stream) and are always forwarded. The
// final non-partial event for a turn typically repeats the full settled
// text, so it's only forwarded when nothing has been streamed yet for that
// author -- that covers turns that never streamed partials at all, so no
// text is ever silently dropped. A blank-line break is inserted between
// consecutive turns from different authors (mirrors extractGeapText()'s
// "\n\n"-joined segments).
function createStreamDeltaPlanner() {
  let currentAuthor = null;
  let sentAnyForCurrentAuthor = false;

  function processEvent(event) {
    const deltas = [];
    if (event.author === "user") return deltas;

    if (event.author !== currentAuthor) {
      if (currentAuthor !== null && sentAnyForCurrentAuthor) {
        deltas.push("\n\n");
      }
      currentAuthor = event.author;
      sentAnyForCurrentAuthor = false;
    }

    const parts = event.content?.parts || [];
    const text = parts
      .map((part) => part.text)
      .filter((t) => typeof t === "string" && t.length > 0)
      .join("");

    if (!text) return deltas;

    if (event.partial) {
      deltas.push(text);
      sentAnyForCurrentAuthor = true;
    } else if (!sentAnyForCurrentAuthor) {
      deltas.push(text);
      sentAnyForCurrentAuthor = true;
    }

    return deltas;
  }

  return { processEvent };
}

// Reuses one Agent Engine session per browser session (stored in req.session) so the
// hosted agent retains conversation memory across chat turns instead of starting fresh
// on every message. Creates one via the `:query` REST method (class_method
// "async_create_session") the first time, then hands back the cached id on later calls.
async function getOrCreateGeapSession(req, accessToken) {
  if (req.session.geapSessionId) {
    return req.session.geapSessionId;
  }

  const url = `https://${GEAP_ENGINE_LOCATION}-aiplatform.googleapis.com/v1/projects/${GEAP_ENGINE_PROJECT}/locations/${GEAP_ENGINE_LOCATION}/reasoningEngines/${GEAP_ENGINE_ID}:query`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${accessToken}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      class_method: "async_create_session",
      input: { user_id: req.sessionID }
    })
  });

  const rawText = await response.text();
  if (!response.ok) {
    throw new Error(`Vertex AI API Error ${response.status}: ${rawText}`);
  }

  const data = JSON.parse(rawText);
  const sessionId = data.output && data.output.id;
  if (!sessionId) {
    throw new Error(`GEAP session creation did not return a session id: ${rawText}`);
  }

  req.session.geapSessionId = sessionId;
  await new Promise((resolve, reject) => {
    req.session.save((err) => (err ? reject(err) : resolve()));
  });

  return sessionId;
}

app.post("/api/geap/query", async (req, res) => {
  const { query } = req.body;
  console.log(`[GEAP] Query received: ${query}`);
  if (!query) {
    return res.status(400).json({ error: "Missing query" });
  }

  try {
    const client = await auth.getClient();
    const tokenResponse = await client.getAccessToken();
    const accessToken = tokenResponse.token;

    const streamQueryUrl = `https://${GEAP_ENGINE_LOCATION}-aiplatform.googleapis.com/v1/projects/${GEAP_ENGINE_PROJECT}/locations/${GEAP_ENGINE_LOCATION}/reasoningEngines/${GEAP_ENGINE_ID}:streamQuery`;

    async function startStreamQuery(sessionId) {
      return fetch(streamQueryUrl, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${accessToken}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          class_method: "stream_query",
          input: {
            message: query,
            user_id: req.sessionID,
            session_id: sessionId,
            // Without this, ADK's RunConfig defaults to StreamingMode.NONE:
            // the agent yields one single, final event per turn with no
            // partial/token-level events at all, regardless of this being
            // the ":streamQuery" REST method. SSE mode is what actually
            // makes the model stream progressively.
            run_config: { streaming_mode: "sse" }
          }
        })
      });
    }

    let sessionId = await getOrCreateGeapSession(req, accessToken);
    let upstream = await startStreamQuery(sessionId);

    // The cached session may have expired or been evicted server-side; recreate once and retry.
    if (!upstream.ok) {
      const errText = await upstream.text();
      const isMissingSession = /session/i.test(errText) && /not found/i.test(errText);
      if (isMissingSession) {
        console.error("[GEAP] Cached session rejected, recreating:", errText);
        delete req.session.geapSessionId;
        sessionId = await getOrCreateGeapSession(req, accessToken);
        upstream = await startStreamQuery(sessionId);
        if (!upstream.ok) {
          throw new Error(`Vertex AI API Error ${upstream.status}: ${await upstream.text()}`);
        }
      } else {
        throw new Error(`Vertex AI API Error ${upstream.status}: ${errText}`);
      }
    }

    // Relay the agent's reply as Server-Sent Events as soon as each text delta
    // arrives, instead of buffering the whole (potentially long, multi-agent)
    // turn before sending anything back to the browser. Vertex genuinely
    // streams this (see the `event.partial` flag below) -- buffering it here
    // was throwing that away and adding the agent's full generation time to
    // every request's time-to-first-byte.
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    res.setHeader("X-Accel-Buffering", "no"); // disable buffering on nginx-style reverse proxies, if any sit in front
    res.flushHeaders();

    const parser = createIncrementalGeapEventParser();
    const planner = createStreamDeltaPlanner();
    const decoder = new TextDecoder("utf-8");
    const reader = upstream.body.getReader();
    const allEvents = [];

    function sendDelta(delta) {
      res.write(`data: ${JSON.stringify({ delta })}\n\n`);
    }

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const events = parser.feed(decoder.decode(value, { stream: true }));

      for (const event of events) {
        allEvents.push(event);
        for (const delta of planner.processEvent(event)) {
          sendDelta(delta);
        }
      }
    }

    const widgetSentinel = extractWidgetSignal(allEvents);
    const a2uiPayload = extractA2uiPayload(allEvents);
    console.log(`[GEAP] Stream complete. Widget signal: ${widgetSentinel || "(none)"}, A2UI surface: ${a2uiPayload ? a2uiPayload.messages?.[0]?.surfaceId : "(none)"}`);
    res.write(`data: ${JSON.stringify({ done: true, widget: widgetSentinel, a2ui: a2uiPayload })}\n\n`);
    res.end();
  } catch (error) {
    console.error("[GEAP] Error calling GEAP agent:", error);
    if (!res.headersSent) {
      res.status(500).json({ error: error.message });
    } else {
      res.write(`data: ${JSON.stringify({ error: error.message })}\n\n`);
      res.end();
    }
  }
});

app.get(appRoutes, (_req, res) => {
  res.sendFile(path.join(publicDir, "index.html"));
});

app.use((_req, res) => {
  res.status(404).sendFile(path.join(publicDir, "index.html"));
});

app.listen(port, () => {
  console.log(`GEAP E*TRADE POC running at http://localhost:${port}`);
});

// Exported for unit testing the pure event-stream parsing/planning helpers in
// isolation, without needing a live Vertex AI/Agent Engine call.
module.exports = {
  createIncrementalGeapEventParser,
  parseGeapStreamEvents,
  extractGeapText,
  extractWidgetSignal,
  extractA2uiPayload,
  createStreamDeltaPlanner
};
