import re

with open('frontend/src/components/chat/MessageBubble.tsx', 'r') as f:
    content = f.read()

# Add imports
imports = """import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
"""
if 'import ReactMarkdown' not in content:
    content = content.replace("import React, { useState } from 'react';", "import React, { useState } from 'react';\n" + imports)

# Find renderFormattedContent
start_str = "  const renderFormattedContent = (content: string) => {"
end_str = "return <div className=\"space-y-0.5\">{elements}</div>;\n  };"

start_idx = content.find(start_str)
end_idx = content.find(end_str) + len(end_str)

new_func = """  const renderFormattedContent = (content: string) => {
    if (!content) return null;

    // Convert [[Doc: filename.pdf, p. X]] to markdown links for interception
    // We encode the citation data into the hash of the URL: #cite|||filename.pdf|||X
    const processedContent = content.replace(
      /\\[\\[Doc:\\s*(.*?),\\s*p\\.\\s*(\\d+)(?:\\s*-\\s*.*?)?\\]\\]/g,
      '[Citation](#cite|||$1|||$2)'
    );

    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, href, children, ...props }) => {
            if (href?.startsWith('#cite|||')) {
              const parts = href.split('|||');
              const fileName = parts[1] || 'Unknown';
              const pageNum = parts[2] || '1';
              return (
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onOpenCitationDrawer?.();
                  }}
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 mx-1 text-xs font-semibold text-emerald-300 bg-emerald-950/80 border border-emerald-700/60 rounded hover:bg-emerald-900 hover:text-emerald-100 transition-colors shadow-sm cursor-pointer align-middle"
                  title={`View citation in ${fileName} (p. ${pageNum})`}
                >
                  <FileText className="w-3 h-3 text-emerald-400" />
                  <span className="truncate max-w-[150px]">{fileName}</span>
                  <span className="text-emerald-400 font-mono text-[10px]">p.{pageNum}</span>
                </button>
              );
            }
            return (
              <a href={href} className="text-emerald-400 hover:underline" target="_blank" rel="noopener noreferrer" {...props}>
                {children}
              </a>
            );
          },
          table: ({ node, ...props }) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full text-sm text-left text-slate-200 border border-slate-700 rounded-lg overflow-hidden" {...props} />
            </div>
          ),
          thead: ({ node, ...props }) => <thead className="bg-slate-800/80 text-xs uppercase text-slate-400" {...props} />,
          th: ({ node, ...props }) => <th className="px-4 py-3 border-b border-slate-700" {...props} />,
          td: ({ node, ...props }) => <td className="px-4 py-3 border-b border-slate-700/60" {...props} />,
          tr: ({ node, ...props }) => <tr className="hover:bg-slate-800/40" {...props} />,
          p: ({ node, ...props }) => <p className="leading-relaxed my-2" {...props} />,
          ul: ({ node, ...props }) => <ul className="list-disc ml-6 my-2" {...props} />,
          ol: ({ node, ...props }) => <ol className="list-decimal ml-6 my-2" {...props} />,
          li: ({ node, ...props }) => <li className="my-1" {...props} />,
          h1: ({ node, ...props }) => <h1 className="text-2xl font-bold text-slate-100 mt-5 mb-3" {...props} />,
          h2: ({ node, ...props }) => <h2 className="text-xl font-bold text-slate-100 mt-4 mb-2" {...props} />,
          h3: ({ node, ...props }) => <h3 className="text-lg font-bold text-slate-100 mt-3 mb-1.5 text-emerald-400" {...props} />,
          h4: ({ node, ...props }) => <h4 className="text-base font-bold text-slate-100 mt-2 mb-1" {...props} />,
          blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-emerald-500/50 pl-4 py-1 my-3 bg-slate-800/30 italic text-slate-300" {...props} />,
          code: ({ node, inline, className, children, ...props }: any) => {
            return inline ? (
              <code className="bg-slate-800 text-emerald-300 px-1.5 py-0.5 rounded text-xs font-mono" {...props}>{children}</code>
            ) : (
              <pre className="bg-slate-900 p-4 rounded-xl border border-slate-700 overflow-x-auto my-3">
                <code className="text-slate-300 text-sm font-mono" {...props}>{children}</code>
              </pre>
            );
          },
        }}
      >
        {processedContent}
      </ReactMarkdown>
    );
  };"""

content = content[:start_idx] + new_func + content[end_idx:]

with open('frontend/src/components/chat/MessageBubble.tsx', 'w') as f:
    f.write(content)

print("Done")
