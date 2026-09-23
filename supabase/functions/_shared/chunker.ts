// ============================================================================
// RFPANDA — Markdown-Aware Semantic Chunker for RFP Documents
// ============================================================================

export interface ProcessedChunk {
  chunkIndex: number;
  content: string;
  pageNumber: number | null;
  sectionHeader: string | null;
  hasTable: boolean;
  tokenCount: number;
  metadata: {
    has_table: boolean;
    section_header: string | null;
    page_number: number | null;
    char_count: number;
    token_count: number;
    [key: string]: unknown;
  };
}

export interface ChunkerOptions {
  targetTokens?: number; // Default: 600 tokens (~2400 chars)
  overlapTokens?: number; // Default: 100 tokens (~400 chars)
  maxTokens?: number; // Default: 1000 tokens (~4000 chars)
}

interface MarkdownBlock {
  type: "heading" | "table" | "code" | "paragraph" | "page_break";
  content: string;
  headingLevel?: number;
  headingText?: string;
  pageNumber?: number | null;
  tableHeader?: string;
}

export class SemanticChunker {
  private targetTokens: number;
  private overlapTokens: number;
  private maxTokens: number;

  constructor(options: ChunkerOptions = {}) {
    this.targetTokens = options.targetTokens ?? 600;
    this.overlapTokens = options.overlapTokens ?? 100;
    this.maxTokens = options.maxTokens ?? 1000;
  }

  /**
   * Fast token estimation (1 token ≈ 4 characters for English text/markdown).
   */
  public estimateTokens(text: string): number {
    if (!text || text.length === 0) return 0;
    return Math.ceil(text.length / 4);
  }

  /**
   * Main entry point: chunks markdown text preserving table integrity and header context.
   */
  public chunkMarkdown(markdown: string): ProcessedChunk[] {
    if (!markdown || markdown.trim().length === 0) {
      return [];
    }

    const normalized = markdown.replace(/\r\n/g, "\n");
    const blocks = this.parseBlocks(normalized);

    if (blocks.length === 0) {
      return [];
    }

    const chunks: ProcessedChunk[] = [];
    let currentChunkIndex = 0;

    let buffer = "";
    let bufferTokens = 0;
    let activeHeader: string | null = null;
    let activePageNumber: number | null = null;
    const activeHeaderStack: { level: number; text: string }[] = [];

    const flushBuffer = (retainOverlap = true) => {
      const trimmed = buffer.trim();
      if (trimmed.length === 0) {
        buffer = "";
        bufferTokens = 0;
        return;
      }

      // Check if buffer is just a heading or context line with no body text
      const lines = trimmed.split("\n").map((l) => l.trim()).filter(Boolean);
      const isOnlyHeading = lines.every((l) =>
        l.startsWith("#") || l.startsWith("[Context:")
      );
      if (isOnlyHeading) {
        // Do not emit a standalone heading chunk; heading is already preserved in activeHeader
        buffer = "";
        bufferTokens = 0;
        return;
      }

      const chunkPage = activePageNumber ?? this.extractPageNumber(trimmed);
      const chunkHeader = activeHeader ?? this.extractHeadingContext(trimmed);
      const hasTable = this.detectTable(trimmed);
      const tokens = this.estimateTokens(trimmed);

      chunks.push({
        chunkIndex: currentChunkIndex++,
        content: trimmed,
        pageNumber: chunkPage,
        sectionHeader: chunkHeader,
        hasTable,
        tokenCount: tokens,
        metadata: {
          has_table: hasTable,
          section_header: chunkHeader,
          page_number: chunkPage,
          char_count: trimmed.length,
          token_count: tokens,
        },
      });

      if (retainOverlap && this.overlapTokens > 0) {
        // Extract overlap from trailing sentences or lines
        const overlapText = this.extractOverlapText(
          trimmed,
          this.overlapTokens,
        );
        if (overlapText.length > 0) {
          const contextPrefix = chunkHeader
            ? `[Context: ${chunkHeader}]\n`
            : "";
          buffer = contextPrefix + overlapText;
          bufferTokens = this.estimateTokens(buffer);
          return;
        }
      }

      buffer = "";
      bufferTokens = 0;
    };

    for (let i = 0; i < blocks.length; i++) {
      const block = blocks[i];

      // Page break or new page marker: flush buffer so pages are partitioned cleanly
      if (
        block.type === "page_break" ||
        (block.pageNumber !== null && block.pageNumber !== undefined &&
          block.pageNumber !== activePageNumber)
      ) {
        if (
          activePageNumber !== null && block.pageNumber !== null &&
          block.pageNumber !== activePageNumber
        ) {
          flushBuffer(false);
        }
        if (block.pageNumber !== null && block.pageNumber !== undefined) {
          activePageNumber = block.pageNumber;
        }
        if (block.type === "page_break") {
          continue;
        }
      }

      // Update header hierarchy tracking
      if (block.type === "heading") {
        const level = block.headingLevel || 1;
        const text = block.headingText ||
          block.content.replace(/^#+\s*/, "").trim();

        // Maintain heading stack
        while (
          activeHeaderStack.length > 0 &&
          activeHeaderStack[activeHeaderStack.length - 1].level >= level
        ) {
          activeHeaderStack.pop();
        }
        activeHeaderStack.push({ level, text });
        activeHeader = activeHeaderStack.map((h) => h.text).join(" > ");
      }

      const blockTokens = this.estimateTokens(block.content);

      // Case 1: Large Table that exceeds maxTokens by itself
      if (block.type === "table" && blockTokens > this.maxTokens) {
        flushBuffer(false);
        const splitTableChunks = this.splitLargeTable(
          block,
          activeHeader,
          activePageNumber,
        );
        for (const subChunk of splitTableChunks) {
          chunks.push({
            chunkIndex: currentChunkIndex++,
            content: subChunk.content,
            pageNumber: subChunk.pageNumber,
            sectionHeader: subChunk.sectionHeader,
            hasTable: true,
            tokenCount: subChunk.tokenCount,
            metadata: {
              has_table: true,
              section_header: subChunk.sectionHeader,
              page_number: subChunk.pageNumber,
              char_count: subChunk.content.length,
              token_count: subChunk.tokenCount,
            },
          });
        }
        buffer = "";
        bufferTokens = 0;
        continue;
      }

      // Case 2: Large Paragraph or Code block that exceeds maxTokens
      if (blockTokens > this.maxTokens) {
        flushBuffer(false);
        const subChunks = this.splitLargeText(
          block.content,
          activeHeader,
          activePageNumber,
        );
        for (const sc of subChunks) {
          chunks.push({
            chunkIndex: currentChunkIndex++,
            content: sc.content,
            pageNumber: sc.pageNumber,
            sectionHeader: sc.sectionHeader,
            hasTable: sc.hasTable,
            tokenCount: sc.tokenCount,
            metadata: {
              has_table: sc.hasTable,
              section_header: sc.sectionHeader,
              page_number: sc.pageNumber,
              char_count: sc.content.length,
              token_count: sc.tokenCount,
            },
          });
        }
        buffer = "";
        bufferTokens = 0;
        continue;
      }

      // Case 3: Adding this block exceeds targetTokens
      if (
        bufferTokens + blockTokens > this.targetTokens &&
        buffer.trim().length > 0
      ) {
        if (
          bufferTokens + blockTokens <= this.maxTokens &&
          block.type !== "heading"
        ) {
          buffer += "\n\n" + block.content;
          bufferTokens += blockTokens;
        } else {
          flushBuffer(true);
          if (buffer.trim().length > 0) {
            buffer += "\n\n" + block.content;
            bufferTokens = this.estimateTokens(buffer);
          } else {
            const headerPrefix = activeHeader && block.type !== "heading"
              ? `[Context: ${activeHeader}]\n`
              : "";
            buffer = headerPrefix + block.content;
            bufferTokens = this.estimateTokens(buffer);
          }
        }
      } else {
        // Normal accumulation
        if (buffer.trim().length === 0) {
          const headerPrefix = activeHeader && block.type !== "heading"
            ? `[Context: ${activeHeader}]\n`
            : "";
          buffer = headerPrefix + block.content;
        } else {
          buffer += "\n\n" + block.content;
        }
        bufferTokens = this.estimateTokens(buffer);
      }
    }

    // Flush any remaining content
    flushBuffer(false);

    return chunks;
  }

  /**
   * Helper to detect if a text contains a markdown table.
   */
  private detectTable(text: string): boolean {
    const lines = text.split("\n").map((l) => l.trim());
    const tableLines = lines.filter((l) =>
      l.startsWith("|") && l.endsWith("|") && l.length > 2
    );
    return tableLines.length >= 2;
  }

  /**
   * Parses raw markdown into structured blocks.
   */
  private parseBlocks(markdown: string): MarkdownBlock[] {
    const lines = markdown.split("\n");
    const blocks: MarkdownBlock[] = [];

    let currentLines: string[] = [];
    let inCodeBlock = false;
    let inTable = false;
    let tableHeaderLines: string[] = [];
    let currentPage: number | null = null;

    const commitCurrent = (type: MarkdownBlock["type"] = "paragraph") => {
      if (currentLines.length === 0) return;
      const text = currentLines.join("\n").trim();
      if (text.length > 0) {
        blocks.push({
          type,
          content: text,
          pageNumber: currentPage,
          tableHeader: type === "table" && tableHeaderLines.length > 0
            ? tableHeaderLines.join("\n")
            : undefined,
        });
      }
      currentLines = [];
      tableHeaderLines = [];
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      // Check for Page Markers (e.g. "## Page 1", "<!-- Page 2 -->", "=== Page 3 ===", "--- Page 4 ---")
      const pageMatch = trimmed.match(
        /^(?:#{1,3}\s*)?(?:Page|PAGE|page)\s+(\d+)|<!--\s*(?:Page|PAGE|page)\s+(\d+)\s*-->/,
      );
      if (pageMatch) {
        const pageNum = parseInt(pageMatch[1] || pageMatch[2], 10);
        if (!isNaN(pageNum)) {
          commitCurrent("paragraph");
          currentPage = pageNum;
          blocks.push({
            type: "page_break",
            content: line.trim(),
            pageNumber: pageNum,
          });
          continue;
        }
      }

      // Check for Code Block delimiters
      if (trimmed.startsWith("```")) {
        if (inCodeBlock) {
          currentLines.push(line);
          commitCurrent("code");
          inCodeBlock = false;
          continue;
        } else {
          commitCurrent("paragraph");
          inCodeBlock = true;
          currentLines.push(line);
          continue;
        }
      }

      if (inCodeBlock) {
        currentLines.push(line);
        continue;
      }

      // Check for Markdown Headings (# Header)
      const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
      if (headingMatch && !inTable) {
        commitCurrent("paragraph");
        const level = headingMatch[1].length;
        const headingText = headingMatch[2].trim();
        blocks.push({
          type: "heading",
          content: line.trim(),
          headingLevel: level,
          headingText,
          pageNumber: currentPage,
        });
        continue;
      }

      // Check for Table Rows
      const isTableRow = trimmed.startsWith("|") && trimmed.endsWith("|") &&
        trimmed.length > 1;

      if (isTableRow) {
        if (!inTable) {
          commitCurrent("paragraph");
          inTable = true;
          currentLines.push(line);
        } else {
          currentLines.push(line);
          if (currentLines.length <= 2) {
            tableHeaderLines.push(line);
          }
        }
        continue;
      } else if (inTable) {
        commitCurrent("table");
        inTable = false;
      }

      // Blank lines separate paragraphs
      if (trimmed === "") {
        if (currentLines.length > 0) {
          commitCurrent("paragraph");
        }
        continue;
      }

      // Regular text lines
      currentLines.push(line);
    }

    if (inCodeBlock) {
      commitCurrent("code");
    } else if (inTable) {
      commitCurrent("table");
    } else {
      commitCurrent("paragraph");
    }

    return blocks;
  }

  /**
   * Splits a massive Markdown table by rows while repeating the header row and separator.
   */
  private splitLargeTable(
    block: MarkdownBlock,
    sectionHeader: string | null,
    pageNumber: number | null,
  ): Array<
    {
      content: string;
      pageNumber: number | null;
      sectionHeader: string | null;
      tokenCount: number;
    }
  > {
    const lines = block.content.split("\n").map((l) => l.trim()).filter((l) =>
      l.length > 0
    );
    if (lines.length <= 2) {
      return [{
        content: block.content,
        pageNumber,
        sectionHeader,
        tokenCount: this.estimateTokens(block.content),
      }];
    }

    // Extract table header and separator
    const headerRow = lines[0];
    const separatorRow = lines[1].includes("-")
      ? lines[1]
      : "|" + headerRow.split("|").slice(1, -1).map(() => "---").join("|") +
        "|";
    const headerBlock = `${headerRow}\n${separatorRow}`;
    const headerTokens = this.estimateTokens(headerBlock);

    const dataRows = lines[1].includes("-") ? lines.slice(2) : lines.slice(1);
    const subChunks: Array<
      {
        content: string;
        pageNumber: number | null;
        sectionHeader: string | null;
        tokenCount: number;
      }
    > = [];

    let currentRows: string[] = [];
    let currentTokens = headerTokens;
    const contextPrefix = sectionHeader ? `[Context: ${sectionHeader}]\n` : "";
    const prefixTokens = this.estimateTokens(contextPrefix);

    for (const row of dataRows) {
      const rowTokens = this.estimateTokens(row);
      if (
        prefixTokens + currentTokens + rowTokens > this.targetTokens &&
        currentRows.length > 0
      ) {
        const fullContent = contextPrefix + headerBlock + "\n" +
          currentRows.join("\n");
        subChunks.push({
          content: fullContent,
          pageNumber,
          sectionHeader,
          tokenCount: this.estimateTokens(fullContent),
        });
        currentRows = [row];
        currentTokens = headerTokens + rowTokens;
      } else {
        currentRows.push(row);
        currentTokens += rowTokens;
      }
    }

    if (currentRows.length > 0) {
      const fullContent = contextPrefix + headerBlock + "\n" +
        currentRows.join("\n");
      subChunks.push({
        content: fullContent,
        pageNumber,
        sectionHeader,
        tokenCount: this.estimateTokens(fullContent),
      });
    }

    return subChunks;
  }

  /**
   * Splits a massive paragraph or text block by sentences or words with overlap.
   */
  private splitLargeText(
    text: string,
    sectionHeader: string | null,
    pageNumber: number | null,
  ): Array<
    {
      content: string;
      pageNumber: number | null;
      sectionHeader: string | null;
      tokenCount: number;
      hasTable: boolean;
    }
  > {
    const sentences = text.match(/[^.!?]+[.!?]+(\s+|$)|[^.!?]+$/g) || [text];
    const chunks: Array<
      {
        content: string;
        pageNumber: number | null;
        sectionHeader: string | null;
        tokenCount: number;
        hasTable: boolean;
      }
    > = [];

    const contextPrefix = sectionHeader ? `[Context: ${sectionHeader}]\n` : "";
    let current = contextPrefix;
    let currentTokens = this.estimateTokens(current);

    for (const sentence of sentences) {
      const sentTokens = this.estimateTokens(sentence);
      if (
        currentTokens + sentTokens > this.targetTokens &&
        current.trim().length > contextPrefix.trim().length
      ) {
        chunks.push({
          content: current.trim(),
          pageNumber,
          sectionHeader,
          tokenCount: this.estimateTokens(current.trim()),
          hasTable: false,
        });

        // Add overlap
        const overlap = this.extractOverlapText(current, this.overlapTokens);
        current = contextPrefix + (overlap ? `... ${overlap}\n` : "") +
          sentence;
        currentTokens = this.estimateTokens(current);
      } else {
        current += sentence;
        currentTokens += sentTokens;
      }
    }

    if (current.trim().length > 0) {
      chunks.push({
        content: current.trim(),
        pageNumber,
        sectionHeader,
        tokenCount: this.estimateTokens(current.trim()),
        hasTable: false,
      });
    }

    return chunks;
  }

  /**
   * Extracts overlapping text (~overlapTokens tokens) from the end of a chunk.
   */
  private extractOverlapText(text: string, maxTokens: number): string {
    const words = text.split(/\s+/).filter(Boolean);
    const targetWords = Math.floor(maxTokens * 0.75);
    if (words.length <= targetWords) {
      return "";
    }
    return words.slice(-targetWords).join(" ");
  }

  /**
   * Extracts page number from text if present.
   */
  private extractPageNumber(text: string): number | null {
    const match = text.match(
      /(?:Page|PAGE|page)\s+(\d+)|<!--\s*(?:Page|PAGE|page)\s+(\d+)\s*-->/,
    );
    if (match) {
      const num = parseInt(match[1] || match[2], 10);
      if (!isNaN(num)) return num;
    }
    return null;
  }

  /**
   * Extracts heading context if present in chunk.
   */
  private extractHeadingContext(text: string): string | null {
    const match = text.match(/^(?:\[Context:\s*([^\]]+)\]|#{1,6}\s+(.+))$/m);
    if (match) {
      return (match[1] || match[2]).trim();
    }
    return null;
  }
}
