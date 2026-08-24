const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const geminiSource = fs.readFileSync(
  path.resolve(__dirname, '..', '..', 'public', 'js', 'gemini.js'),
  'utf8'
);

function loadGeminiApi(mockClient) {
  global.App = { getApiKey: () => 'test-key' };
  global.AgentManager = {
    callTool: async () => 'ACCOUNT SUMMARY',
  };

  eval(geminiSource + '\nglobal.GeminiAPI = GeminiAPI;');
  global.GeminiAPI.__setClientForTests(mockClient);

  return global.GeminiAPI;
}

test('GeminiAPI preserves functionCall thought signatures in tool replay', async () => {
  const capturedRequests = [];
  const firstResponseChunks = [
    {
      candidates: [{
        content: {
          parts: [{
            functionCall: { name: 'getAccountSummary', args: {} },
            thought_signature: 'sig-123',
          }],
        },
      }],
      text: '',
    },
  ];
  const secondResponseChunks = [{ text: 'done' }];

  const mockClient = {
    models: {
      async *generateContentStream(request) {
        capturedRequests.push(request);
        const chunks = capturedRequests.length === 1 ? firstResponseChunks : secondResponseChunks;
        for (const chunk of chunks) {
          yield chunk;
        }
      },
    },
  };

  const geminiApi = loadGeminiApi(mockClient);
  const result = await geminiApi.sendMessage(
    [{ role: 'user', parts: [{ text: 'summarize my account' }] }],
    'system',
    geminiApi.toolDeclarations
  );

  assert.strictEqual(result, 'done');
  assert.strictEqual(capturedRequests.length, 2);
  assert.deepStrictEqual(capturedRequests[1].contents[1], {
    role: 'model',
    parts: [{
      functionCall: { name: 'getAccountSummary', args: {} },
      thought_signature: 'sig-123',
    }],
  });
});