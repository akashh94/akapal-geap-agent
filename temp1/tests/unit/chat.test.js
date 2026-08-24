const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

// 1. Mock global environment and DOM
global.state = {
  governance: {
    safety: true,
    disclaimers: true,
    pii: true,
    rateLimiting: true,
    escalation: true,
    audit: true
  }
};

global.window = {
  location: {
    pathname: '/accounts'
  }
};

const mockMessagesEl = {
  appendChild: (child) => {
    mockMessagesEl.messages.push(child);
  },
  messages: [],
  get scrollHeight() { return 100; },
  set scrollTop(val) {}
};

global.document = {
  getElementById: (id) => {
    if (id === 'chat-messages') return mockMessagesEl;
    if (id === 'chat-suggestions') return { style: {} };
    if (id === 'chat-avatar') return { textContent: '' };
    if (id === 'chat-agent-name') return { textContent: '' };
    return null;
  },
  createElement: (tag) => {
    const el = {
      className: '',
      innerHTML: '',
      remove: function() {
        const index = mockMessagesEl.messages.indexOf(el);
        if (index > -1) {
          mockMessagesEl.messages.splice(index, 1);
        }
      },
      querySelector: () => ({ innerHTML: '' })
    };
    return el;
  }
};

global.AgentManager = {
  autoRoute: () => 'portfolio-analyst',
  getAgent: () => ({
    id: 'portfolio-analyst',
    name: 'Portfolio Analyst',
    icon: '📊',
    tools: [],
    systemPrompt: ''
  }),
  callTool: () => ''
};

global.BrokerageData = {
  agentActivityLog: [],
  logAgentActivity: (entry) => {
    global.BrokerageData.agentActivityLog.push(entry);
  }
};

global.GeapApp = {
  getApiKey: () => null, // mockResponse path
  renderMarkdown: (text) => text
};

// Real rendering lives in public/js/a2ui/a2ui-view.js (its own test file,
// tests/unit/a2ui-view.test.js); chat.js only needs the encode entry point
// it calls when wiring an A2UI payload into a message bubble.
global.A2uiView = {
  encodePayload: (payload) => Buffer.from(JSON.stringify(payload), 'utf8').toString('base64')
};

global.GeminiAPI = {
  toolDeclarations: [],
  sendMessage: async () => 'Mocked live API response'
};

global.ContextEngine = {
  getContextPayload: () => ({
    platform: { route: '/accounts', time: '', theme: 'dark' },
    user: { name: 'Sree K.', lastLogin: '' },
    account: { selectedId: 'core', netValue: '$0.00', buyingPower: '$0.00' },
    security: { piiRedacted: true, safetyActive: true, disclaimersActive: true }
  }),
  formatContextToMarkdown: () => '=== SYSTEM CONTEXT ===\nMocked Context\n======================='
};

// 2. Load and execute chat.js
const code = fs.readFileSync(path.resolve(__dirname, '..', '..', 'public', 'js', 'chat.js'), 'utf8');
eval(code + '\nglobal.Chat = Chat;');

function resetState() {
  mockMessagesEl.messages = [];
  BrokerageData.agentActivityLog = [];
}

test('Chat - Preprocessing and Safety Filter', async (t) => {
  // Toggled ON: should block jailbreak queries
  resetState();
  state.governance.safety = true;
  await Chat.sendMessage('how to jailbreak a model?');
  await new Promise(resolve => setTimeout(resolve, 900));

  const assistantMsg = mockMessagesEl.messages.find(m => m.className.includes('assistant'));
  assert.ok(assistantMsg, 'Should have received assistant response');
  assert.ok(assistantMsg.innerHTML.includes('Safety Alert'), 'Query should be blocked by safety warning');

  // Toggled OFF: should let it pass
  resetState();
  state.governance.safety = false;
  await Chat.sendMessage('how to jailbreak a model?');
  await new Promise(resolve => setTimeout(resolve, 1100));

  const assistantMsg2 = mockMessagesEl.messages.find(m => m.className.includes('assistant'));
  assert.ok(assistantMsg2, 'Should have received assistant response');
  assert.ok(!assistantMsg2.innerHTML.includes('Safety Alert'), 'Safety block should not trigger when toggled off');
});

test('Chat - PII Redaction', async (t) => {
  // Toggled ON: should redact sensitive details in user message
  resetState();
  state.governance.pii = true;
  await Chat.sendMessage('My SSN is 999-88-7777 and my account is 1234-5678');

  const userMsg = mockMessagesEl.messages.find(m => m.className.includes('user'));
  assert.ok(userMsg, 'Should have user message');
  assert.ok(userMsg.innerHTML.includes('[REDACTED SSN]'), 'SSN should be redacted');
  assert.ok(userMsg.innerHTML.includes('[REDACTED ACCOUNT]'), 'Account number should be redacted');

  // Toggled OFF: should preserve raw credentials
  resetState();
  state.governance.pii = false;
  await Chat.sendMessage('My SSN is 999-88-7777');

  const userMsgRaw = mockMessagesEl.messages.find(m => m.className.includes('user'));
  assert.ok(userMsgRaw);
  assert.ok(userMsgRaw.innerHTML.includes('999-88-7777'), 'SSN should remain unredacted when toggled off');
});

test('Chat - Compliance Disclaimers', async (t) => {
  // Toggled ON: investment query triggers disclaimer
  resetState();
  state.governance.disclaimers = true;
  await Chat.sendMessage('explain my portfolio');
  await new Promise(resolve => setTimeout(resolve, 1100));

  const msg = mockMessagesEl.messages.find(m => m.className.includes('assistant'));
  assert.ok(msg);
  assert.ok(msg.innerHTML.includes('Compliance Disclaimer'), 'Disclaimer should be present on investment responses');

  // Toggled OFF: no disclaimer
  resetState();
  state.governance.disclaimers = false;
  await Chat.sendMessage('explain my portfolio');
  await new Promise(resolve => setTimeout(resolve, 1100));

  const msgNoDisc = mockMessagesEl.messages.find(m => m.className.includes('assistant'));
  assert.ok(msgNoDisc);
  assert.ok(!msgNoDisc.innerHTML.includes('Compliance Disclaimer'), 'Disclaimer should be omitted when toggled off');
});

test('Chat - Human Escalation Trigger', async (t) => {
  // Toggled ON: money transfer query triggers contact card
  resetState();
  state.governance.escalation = true;
  await Chat.sendMessage('withdraw money');
  await new Promise(resolve => setTimeout(resolve, 1100));

  const msg = mockMessagesEl.messages.find(m => m.className.includes('assistant'));
  assert.ok(msg);
  assert.ok(msg.innerHTML.includes('Need Assistance?'), 'Escalation advice should be present');
  assert.ok(msg.innerHTML.includes('Contact a Human Agent'), 'Escalation contact link should be present');

  // Toggled OFF: no contact card
  resetState();
  state.governance.escalation = false;
  await Chat.sendMessage('withdraw money');
  await new Promise(resolve => setTimeout(resolve, 1100));

  const msgNoEsc = mockMessagesEl.messages.find(m => m.className.includes('assistant'));
  assert.ok(msgNoEsc);
  assert.ok(!msgNoEsc.innerHTML.includes('Need Assistance?'), 'Escalation block should be omitted when toggled off');
});

test('Chat - Compliance Audit Logging', async (t) => {
  // Toggled ON: audit logs should populate
  resetState();
  state.governance.audit = true;
  await Chat.sendMessage('test query');
  await new Promise(resolve => setTimeout(resolve, 1100));

  assert.ok(BrokerageData.agentActivityLog.length > 0, 'Should have logged activity');

  // Toggled OFF: no logs
  resetState();
  state.governance.audit = false;
  await Chat.sendMessage('test query');
  await new Promise(resolve => setTimeout(resolve, 1100));

  assert.strictEqual(BrokerageData.agentActivityLog.length, 0, 'Should not log activity when toggled off');
});

test('Chat - Compliance Audit Log PII Scrubbing', async (t) => {
  // Bubble PII toggled OFF: bubble shows raw PII, but compliance log MUST redact it!
  resetState();
  state.governance.audit = true;
  state.governance.pii = false; // Bubble redaction off

  await Chat.sendMessage('My SSN is 999-88-7777');
  await new Promise(resolve => setTimeout(resolve, 1100));

  // Check user bubble has raw SSN
  const userMsg = mockMessagesEl.messages.find(m => m.className.includes('user'));
  assert.ok(userMsg);
  assert.ok(userMsg.innerHTML.includes('999-88-7777'), 'User chat bubble should show raw SSN when pii redaction is disabled');

  // Check compliance audit log is redacted
  assert.ok(BrokerageData.agentActivityLog.length > 0);
  const logEntry = BrokerageData.agentActivityLog[0];
  assert.ok(!logEntry.query.includes('999-88-7777'), 'Compliance log should not contain raw SSN');
  assert.ok(logEntry.query.includes('[REDACTED SSN]'), 'Compliance log should contain redacted placeholder');
});

test('Chat - Risk Analysis Query & Rebalance Form Widget', async (t) => {
  resetState();
  state.governance.disclaimers = false; // Disable disclaimers to keep markup comparison simpler
  await Chat.sendMessage('Run a comprehensive risk analysis on my portfolios and active account holdings.');
  await new Promise(resolve => setTimeout(resolve, 1100));

  const assistantMsg = mockMessagesEl.messages.find(m => m.className.includes('assistant'));
  assert.ok(assistantMsg, 'Should have received assistant response');
  assert.ok(assistantMsg.innerHTML.includes('Technology Sector'), 'Should contain comparison table header');
  assert.ok(assistantMsg.innerHTML.includes('chat-rebalance-card'), 'Should render rebalance form widget markup');
  assert.ok(assistantMsg.innerHTML.includes('MSFT'), 'Should show trade detail MSFT');
  assert.ok(assistantMsg.innerHTML.includes('BND'), 'Should show trade detail BND');
});

test('Chat - Retirement query routes to planning_agent and renders the A2UI dashboard', async (t) => {
  resetState();
  state.governance.disclaimers = false;
  state.aiSettings = { assistantMode: 'geap' };

  // Retirement/planning is no longer a client-side mock -- it's a real
  // supervisor.py route to planning_agent, which signals the client via a
  // render_retirement_dashboard functionResponse. server.js surfaces that
  // as an `a2ui` field on the final SSE event (see extractA2uiPayload in
  // server.js); simulate that here rather than the old canned markdown.
  const originalFetch = global.fetch;
  const envelope = {
    version: 'a2ui/0.9',
    catalogId: 'geap.planning.v1',
    messages: [
      { type: 'createSurface', surfaceId: 'retirement-dashboard', root: 'root' },
      {
        type: 'updateComponents',
        surfaceId: 'retirement-dashboard',
        components: [
          { id: 'root', type: 'surface', props: { title: 'GEAP Intelligent Retirement Advisor' }, children: ['stat-savings'] },
          { id: 'stat-savings', type: 'stat_tile', props: { label: 'Retirement Savings', value: '$84,230.15' }, children: [] }
        ]
      },
      { type: 'updateDataModel', surfaceId: 'retirement-dashboard', data: {} }
    ]
  };
  global.fetch = async (url) => {
    if (url !== '/api/geap/query') return { ok: false };
    const encoder = new TextEncoder();
    const chunks = [
      encoder.encode('data: {"delta":"Here is your retirement health check."}\n\n'),
      encoder.encode(`data: ${JSON.stringify({ done: true, widget: '', a2ui: envelope })}\n\n`)
    ];
    let i = 0;
    return {
      ok: true,
      body: { getReader: () => ({ read: async () => (i < chunks.length ? { done: false, value: chunks[i++] } : { done: true, value: undefined }) }) }
    };
  };

  await Chat.sendMessage('Run retirement planning health check.');

  const assistantMsg = mockMessagesEl.messages.find(m => m.className.includes('assistant'));
  assert.ok(assistantMsg, 'Should have received assistant response');
  assert.ok(assistantMsg.innerHTML.includes('retirement health check'), 'Should contain the agent\'s prose reply');
  assert.ok(assistantMsg.innerHTML.includes('<a2ui-view'), 'Should mount the a2ui-view web component');
  assert.ok(assistantMsg.innerHTML.includes('data-payload='), 'a2ui-view should carry the encoded envelope');

  const decoded = JSON.parse(Buffer.from(assistantMsg.innerHTML.match(/data-payload="([^"]+)"/)[1], 'base64').toString('utf8'));
  assert.strictEqual(decoded.messages[0].surfaceId, 'retirement-dashboard');

  global.fetch = originalFetch;
});

test('Chat - Alert Triage Query Interception', async (t) => {
  resetState();
  state.governance.disclaimers = false;
  
  // Set a dummy API key to simulate live mode
  const originalGetApiKey = GeapApp.getApiKey;
  GeapApp.getApiKey = () => 'dummy-api-key';

  await Chat.sendMessage('Triage my active alerts.');
  await new Promise(resolve => setTimeout(resolve, 1100));

  const assistantMsg = mockMessagesEl.messages.find(m => m.className.includes('assistant'));
  assert.ok(assistantMsg, 'Should have received assistant response');
  assert.ok(assistantMsg.innerHTML.includes('Alert Triage & Recommendations'), 'Should show structured alert triage card even when API key is active');
  assert.ok(assistantMsg.innerHTML.includes('MSFT'), 'Should include details about MSFT concentration');

  // Restore the original getApiKey function
  GeapApp.getApiKey = originalGetApiKey;
});

test('Chat - GEAP mode routes generic queries through server.js, never Gemini directly', async (t) => {
  resetState();
  state.aiSettings = { assistantMode: 'geap' };

  // Mock fetch for the API call; GeminiAPI.sendMessage would throw if called, proving it's bypassed.
  // server.js relays the reply as SSE frames, so the mock response needs a
  // streaming body (a reader yielding chunks), not a plain .json() response.
  const originalFetch = global.fetch;
  const originalGeminiSend = global.GeminiAPI.sendMessage;
  global.fetch = async (url) => {
    if (url === '/api/geap/query') {
      const encoder = new TextEncoder();
      const chunks = [
        encoder.encode('data: {"delta":"Response from GEAP agent"}\n\n'),
        encoder.encode('data: {"done":true,"widget":""}\n\n')
      ];
      let i = 0;
      return {
        ok: true,
        body: {
          getReader: () => ({
            read: async () => {
              if (i < chunks.length) {
                return { done: false, value: chunks[i++] };
              }
              return { done: true, value: undefined };
            }
          })
        }
      };
    }
    return { ok: false };
  };
  global.GeminiAPI.sendMessage = async () => {
    throw new Error('GeminiAPI.sendMessage should not be called in GEAP mode');
  };

  await Chat.sendMessage('what is my portfolio worth right now?');

  const assistantMsg = mockMessagesEl.messages.find(m => m.className.includes('assistant'));
  assert.ok(assistantMsg, 'Should have received assistant response');
  assert.ok(assistantMsg.innerHTML.includes('Response from GEAP agent'), 'Should show response from GEAP agent');

  global.fetch = originalFetch;
  global.GeminiAPI.sendMessage = originalGeminiSend;
});

test('Chat - Gemini mode still calls GeminiAPI directly, never server.js', async (t) => {
  resetState();
  state.aiSettings = { assistantMode: 'gemini' };

  const originalFetch = global.fetch;
  global.fetch = async () => {
    throw new Error('fetch should not be called in Gemini mode');
  };

  await Chat.sendMessage('what is my portfolio worth right now?');

  const assistantMsg = mockMessagesEl.messages.find(m => m.className.includes('assistant'));
  assert.ok(assistantMsg, 'Should have received assistant response');
  assert.ok(assistantMsg.innerHTML.includes('Mocked live API response'), 'Should show response from GeminiAPI');

  global.fetch = originalFetch;
});

