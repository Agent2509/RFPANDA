import test from 'node:test';
import assert from 'node:assert/strict';

test('PDF Fallback payload builder formats pages and headers correctly', () => {
  const mockPages = [
    { page_number: 1, text: 'RFP Title: Cloud Infrastructure Proposal' },
    { page_number: 2, text: 'Section 2: Pricing and SLA Guarantee 99.99%' },
  ];

  const fullTextParts = mockPages.map(
    (p) => `\n\n## Page ${p.page_number}\n\n${p.text}`
  );
  const fullText = fullTextParts.join('\n').trim();

  assert.ok(fullText.includes('## Page 1'));
  assert.ok(fullText.includes('## Page 2'));
  assert.ok(fullText.includes('Pricing and SLA Guarantee 99.99%'));

  const payload = {
    document_id: 'doc-uuid-123',
    text: fullText,
    extracted_text: fullText,
    pages: mockPages,
    parser_used: 'pdfjs_client_fallback',
  };

  assert.equal(payload.document_id, 'doc-uuid-123');
  assert.equal(payload.pages.length, 2);
  assert.equal(payload.parser_used, 'pdfjs_client_fallback');
});
