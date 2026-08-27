import test from 'node:test';
import assert from 'node:assert/strict';

// Test SSE Stream parser logic matching frontend/src/lib/api-client.ts
async function parseSseStream(mockChunks, callbacks = {}) {
  let accumulatedText = '';
  let extractedSources = [];
  let doneSummary = null;
  let errorReceived = null;

  let buffer = '';

  for (const chunk of mockChunks) {
    buffer += chunk;
    const events = buffer.split(/\r?\n\r?\n/);
    buffer = events.pop() || '';

    for (const rawEvent of events) {
      const trimmed = rawEvent.trim();
      if (!trimmed) continue;

      const lines = trimmed.split(/\r?\n/);
      let eventType = 'message';
      const dataLines = [];

      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.replace(/^event:\s*/, '').trim();
        } else if (line.startsWith('data:')) {
          dataLines.push(line.replace(/^data:\s*/, ''));
        }
      }

      const dataStr = dataLines.join('\n');
      if (!dataStr) continue;

      try {
        const data = JSON.parse(dataStr);

        if (eventType === 'sources' || eventType === 'metadata') {
          if (Array.isArray(data.sources)) {
            extractedSources = data.sources;
            callbacks.onSources?.(extractedSources);
          }
        } else if (eventType === 'token') {
          const tokenDelta = data.delta ?? data.text ?? '';
          if (tokenDelta) {
            accumulatedText += tokenDelta;
            callbacks.onToken?.(tokenDelta);
          }
        } else if (eventType === 'done') {
          doneSummary = data;
          callbacks.onDone?.(data);
        } else if (eventType === 'error') {
          const err = new Error(data.error || 'Query error');
          errorReceived = err;
          callbacks.onError?.(err);
        }
      } catch {
        if (eventType === 'token') {
          accumulatedText += dataStr;
          callbacks.onToken?.(dataStr);
        }
      }
    }
  }

  return {
    text: accumulatedText,
    sources: extractedSources,
    summary: doneSummary,
    error: errorReceived,
  };
}

test('SSE Parser extracts sources, tokens and completion summary correctly', async () => {
  const mockSseStream = [
    'event: sources\ndata: {"sources":[{"chunk_id":"c1","document_id":"d1","file_name":"RFP_Security.pdf","page_number":3,"section_header":"3.1 Encryption","similarity":0.92,"snippet":"AES-256 is required."}]}\n\n',
    'event: token\ndata: {"delta":"According"}\n\n',
    'event: token\ndata: {"delta":" to Section 3.1, "}\n\n',
    'event: token\ndata: {"delta":"AES-256 encryption is mandated."}\n\n',
    'event: done\ndata: {"finish_reason":"stop","model":"llama-3.3-70b-versatile","completion_tokens":12,"total_time_ms":450}\n\n',
  ];

  const tokens = [];
  const result = await parseSseStream(mockSseStream, {
    onToken: (t) => tokens.push(t),
  });

  assert.equal(result.sources.length, 1);
  assert.equal(result.sources[0].file_name, 'RFP_Security.pdf');
  assert.equal(result.sources[0].similarity, 0.92);
  assert.equal(result.text, 'According to Section 3.1, AES-256 encryption is mandated.');
  assert.equal(tokens.length, 3);
  assert.equal(result.summary.model, 'llama-3.3-70b-versatile');
  assert.equal(result.summary.completion_tokens, 12);
});

test('SSE Parser handles fragmented byte buffers split across chunks', async () => {
  const fragmentedChunks = [
    'event: token\ndata: {"de',
    'lta":"Hello "}\n\nevent: token\ndata: {"delta":"World"}\n\n',
  ];

  const result = await parseSseStream(fragmentedChunks);
  assert.equal(result.text, 'Hello World');
});

test('SSE Parser handles error event cleanly', async () => {
  const errorChunks = [
    'event: error\ndata: {"error":"No context found for given query","code":"NO_CONTEXT_FOUND"}\n\n',
  ];

  let capturedError = null;
  const result = await parseSseStream(errorChunks, {
    onError: (err) => {
      capturedError = err;
    },
  });

  assert.ok(result.error);
  assert.equal(result.error.message, 'No context found for given query');
  assert.equal(capturedError?.message, 'No context found for given query');
});
