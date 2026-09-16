const content = `| Area | Key Points | Source |
|------|------------|--------|
| **Project Requirements** | • REQ-001 | [[Doc: Mujeeb_CV_6.pdf, p. 1 - Section 2]] |
`;

const processedContent = content.replace(
  /\[\[Doc:\s*(.*?),\s*p\.\s*(\d+)(?:\s*-\s*.*?)?\]\]/g,
  '[Citation](#cite|||$1|||$2)'
);
console.log(processedContent);
