const test = require('node:test');
const assert = require('node:assert');

// server.js calls app.listen() at module load time as a side effect; give it
// its own port and capture+close the instance so it doesn't collide with
// tests/integration/server.test.js's own listener.
const express = require('express');
const listenOriginal = express.application.listen;
let serverInstance;
express.application.listen = function (...args) {
  serverInstance = listenOriginal.apply(this, args);
  return serverInstance;
};

process.env.PORT = '3097';

const {
  createIncrementalGeapEventParser,
  parseGeapStreamEvents,
  extractGeapText,
  extractWidgetSignal,
  extractA2uiPayload,
  createStreamDeltaPlanner
} = require('../../server.js');

test.after(() => {
  if (serverInstance) {
    serverInstance.close();
  }
});

// ── createIncrementalGeapEventParser / parseGeapStreamEvents ──

test('parseGeapStreamEvents - parses concatenated JSON event objects with nested braces and escapes', () => {
  const raw = '{"a":1}{"b":{"nested":"}"}}{"c":"esc\\"aped\\\\}"}';
  const events = parseGeapStreamEvents(raw);
  assert.deepStrictEqual(events, [{ a: 1 }, { b: { nested: '}' } }, { c: 'esc"aped\\}' }]);
});

test('createIncrementalGeapEventParser - reassembles a single event split char-by-char across feed() calls', () => {
  const parser = createIncrementalGeapEventParser();
  const raw = '{"author":"trade_assistant","content":{"parts":[{"text":"Sell 15 shares"},{"functionCall":{"name":"show_rebalance_widget","args":{}}}]}}';
  let events = [];
  for (const ch of raw) {
    events = events.concat(parser.feed(ch));
  }
  assert.strictEqual(events.length, 1);
  assert.strictEqual(events[0].author, 'trade_assistant');
  assert.strictEqual(events[0].content.parts[0].text, 'Sell 15 shares');
  assert.strictEqual(events[0].content.parts[1].functionCall.name, 'show_rebalance_widget');
});

test('createIncrementalGeapEventParser - handles multiple events split across an arbitrary chunk boundary', () => {
  const parser = createIncrementalGeapEventParser();
  const raw = '{"author":"user","content":{"parts":[{"text":"hi"}]}}' +
    '{"author":"trade_assistant","partial":true,"content":{"parts":[{"text":"Sel"}]}}' +
    '{"author":"trade_assistant","partial":true,"content":{"parts":[{"text":"l MSFT"}]}}';
  const splitPoint = 47; // lands mid-object
  const events = [
    ...parser.feed(raw.slice(0, splitPoint)),
    ...parser.feed(raw.slice(splitPoint))
  ];
  assert.strictEqual(events.length, 3);
  assert.strictEqual(events[1].content.parts[0].text, 'Sel');
  assert.strictEqual(events[2].content.parts[0].text, 'l MSFT');
});

test('createIncrementalGeapEventParser - does not re-emit already-consumed events on later feeds', () => {
  const parser = createIncrementalGeapEventParser();
  const e1 = parser.feed('{"a":1}');
  const e2 = parser.feed('{"b":2}');
  assert.deepStrictEqual(e1, [{ a: 1 }]);
  assert.deepStrictEqual(e2, [{ b: 2 }]);
});

// ── extractGeapText ──

test('extractGeapText - joins non-partial, non-user text and skips partial chunks', () => {
  const events = [
    { author: 'user', content: { parts: [{ text: 'my question' }] } },
    { author: 'trade_assistant', partial: true, content: { parts: [{ text: 'thinking...' }] } },
    { author: 'trade_assistant', content: { parts: [{ text: 'Here is the answer.' }] } }
  ];
  assert.strictEqual(extractGeapText(events), 'Here is the answer.');
});

// ── extractWidgetSignal ──

test('extractWidgetSignal - detects show_rebalance_widget tool call', () => {
  const events = [
    { author: 'trade_assistant', content: { parts: [{ text: 'You should trim MSFT.' }] } },
    { author: 'trade_assistant', content: { parts: [{ functionCall: { name: 'show_rebalance_widget', args: {} } }] } }
  ];
  assert.strictEqual(extractWidgetSignal(events), '[[WIDGET:REBALANCE_FORM]]');
});

test('extractWidgetSignal - returns empty string when no signal tool was called', () => {
  const events = [
    { author: 'trade_assistant', content: { parts: [{ text: 'Just a quote.' }] } },
    { author: 'trade_assistant', content: { parts: [{ functionCall: { name: 'get_quote', args: { symbol: 'AAPL' } } }] } }
  ];
  assert.strictEqual(extractWidgetSignal(events), '');
});

// ── extractA2uiPayload ──

test('extractA2uiPayload - extracts the a2ui envelope from a render_retirement_dashboard functionResponse', () => {
  const envelope = { version: 'a2ui/0.9', catalogId: 'geap.planning.v1', messages: [{ type: 'createSurface', surfaceId: 'retirement-dashboard' }] };
  const events = [
    { author: 'planning_agent', content: { parts: [{ text: 'Here is your retirement health check.' }] } },
    { author: 'planning_agent', content: { parts: [{ functionResponse: { name: 'render_retirement_dashboard', response: { a2ui: envelope } } }] } }
  ];
  assert.deepStrictEqual(extractA2uiPayload(events), envelope);
});

test('extractA2uiPayload - returns null when no A2UI signal tool was called', () => {
  const events = [
    { author: 'planning_agent', content: { parts: [{ text: 'Your retirement age is 65.' }] } },
    { author: 'planning_agent', content: { parts: [{ functionResponse: { name: 'get_retirement_summary', response: { target_age: 65 } } }] } }
  ];
  assert.strictEqual(extractA2uiPayload(events), null);
});

test('extractA2uiPayload - ignores a matching tool name with no a2ui field in its response', () => {
  const events = [
    { author: 'planning_agent', content: { parts: [{ functionResponse: { name: 'render_retirement_dashboard', response: {} } }] } }
  ];
  assert.strictEqual(extractA2uiPayload(events), null);
});

// ── createStreamDeltaPlanner ──

test('createStreamDeltaPlanner - forwards partial deltas as they arrive', () => {
  const planner = createStreamDeltaPlanner();
  const d1 = planner.processEvent({ author: 'trade_assistant', partial: true, content: { parts: [{ text: 'Sel' }] } });
  const d2 = planner.processEvent({ author: 'trade_assistant', partial: true, content: { parts: [{ text: 'l MSFT' }] } });
  assert.deepStrictEqual(d1, ['Sel']);
  assert.deepStrictEqual(d2, ['l MSFT']);
});

test('createStreamDeltaPlanner - skips the echoed user event entirely', () => {
  const planner = createStreamDeltaPlanner();
  const deltas = planner.processEvent({ author: 'user', content: { parts: [{ text: 'what is my portfolio worth?' }] } });
  assert.deepStrictEqual(deltas, []);
});

test('createStreamDeltaPlanner - forwards a non-partial final event only if nothing streamed yet for that author', () => {
  const planner = createStreamDeltaPlanner();
  const partialDeltas = planner.processEvent({ author: 'trade_assistant', partial: true, content: { parts: [{ text: 'Sell MSFT' }] } });
  // Final event for the same author typically repeats the full text -- should NOT be re-forwarded.
  const finalDeltas = planner.processEvent({ author: 'trade_assistant', content: { parts: [{ text: 'Sell MSFT' }] } });
  assert.deepStrictEqual(partialDeltas, ['Sell MSFT']);
  assert.deepStrictEqual(finalDeltas, []);
});

test('createStreamDeltaPlanner - forwards a non-partial event when no partials preceded it (no data loss)', () => {
  const planner = createStreamDeltaPlanner();
  const deltas = planner.processEvent({ author: 'trade_assistant', content: { parts: [{ text: 'Full answer, no streaming.' }] } });
  assert.deepStrictEqual(deltas, ['Full answer, no streaming.']);
});

test('createStreamDeltaPlanner - inserts a blank-line break between different authors, only if something was sent', () => {
  const planner = createStreamDeltaPlanner();
  planner.processEvent({ author: 'user', content: { parts: [{ text: 'hi' }] } }); // skipped, no output
  const supervisorDeltas = planner.processEvent({ author: 'supervisor', content: { parts: [{ text: 'Routing to trade_assistant.' }] } });
  const tradeDeltas = planner.processEvent({ author: 'trade_assistant', content: { parts: [{ text: 'Here is the trade impact.' }] } });
  assert.deepStrictEqual(supervisorDeltas, ['Routing to trade_assistant.']);
  assert.deepStrictEqual(tradeDeltas, ['\n\n', 'Here is the trade impact.']);
});

test('createStreamDeltaPlanner - full turn: parser + planner + widget signal reproduce the same output as the old buffered path', () => {
  const parser = createIncrementalGeapEventParser();
  const planner = createStreamDeltaPlanner();
  const raw = '{"author":"trade_assistant","partial":true,"content":{"parts":[{"text":"Recommendation: sell 50 MSFT, buy BND."}]}}' +
    '{"author":"trade_assistant","content":{"parts":[{"text":"Recommendation: sell 50 MSFT, buy BND."}]}}' +
    '{"author":"trade_assistant","content":{"parts":[{"functionCall":{"name":"show_rebalance_widget","args":{}}}]}}';

  const events = parser.feed(raw);
  let assembled = '';
  for (const event of events) {
    for (const delta of planner.processEvent(event)) {
      assembled += delta;
    }
  }
  const widgetSentinel = extractWidgetSignal(events);
  const output = widgetSentinel ? `${assembled}\n\n${widgetSentinel}` : assembled;

  assert.strictEqual(assembled, 'Recommendation: sell 50 MSFT, buy BND.');
  assert.ok(output.includes('[[WIDGET:REBALANCE_FORM]]'));
});
