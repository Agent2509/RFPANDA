import re
import os

files_to_modify = [
    "/home/mohdfaizanali/Desktop/my projects/rfp-engine/frontend/src/components/chat/ChatInterface.tsx",
    "/home/mohdfaizanali/Desktop/my projects/rfp-engine/frontend/src/components/chat/MessageBubble.tsx",
    "/home/mohdfaizanali/Desktop/my projects/rfp-engine/frontend/src/components/chat/CitationDrawer.tsx",
    "/home/mohdfaizanali/Desktop/my projects/rfp-engine/frontend/src/components/documents/DocumentCard.tsx",
    "/home/mohdfaizanali/Desktop/my projects/rfp-engine/frontend/src/components/documents/DocumentList.tsx",
    "/home/mohdfaizanali/Desktop/my projects/rfp-engine/frontend/src/components/upload/UploadDropzone.tsx",
    "/home/mohdfaizanali/Desktop/my projects/rfp-engine/frontend/src/components/system/MemoryIndicator.tsx",
    "/home/mohdfaizanali/Desktop/my projects/rfp-engine/frontend/src/components/auth/AuthForm.tsx",
    "/home/mohdfaizanali/Desktop/my projects/rfp-engine/frontend/src/components/auth/RouteGuard.tsx"
]

def fix_content(content):
    # Re-parse looking for <button or <Button up to > to replace rounded-2xl with rounded-full
    
    def repl(m):
        return m.group(0).replace('rounded-2xl', 'rounded-full').replace('rounded-xl', 'rounded-full')
        
    content = re.sub(r'<(button|Button)[^>]*>', repl, content, flags=re.DOTALL)
    return content

for filepath in files_to_modify:
    if not os.path.exists(filepath):
        continue
    with open(filepath, 'r') as f:
        content = f.read()
    
    content = fix_content(content)
    
    with open(filepath, 'w') as f:
        f.write(content)

