import os
import re

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

color_mapping = [
    (r"bg-slate-950", r"bg-[#FAFAF8]"),
    (r"bg-slate-900/80", r"bg-white/80"),
    (r"bg-slate-900/50", r"bg-white/50"),
    (r"bg-slate-900/60", r"bg-white/60"),
    (r"bg-slate-900/90", r"bg-white/90"),
    (r"bg-slate-900/95", r"bg-white/95"),
    (r"bg-slate-900", r"bg-white"),
    (r"bg-slate-850/80", r"bg-stone-50/80"),
    (r"bg-slate-850/70", r"bg-stone-50/70"),
    (r"bg-slate-850/50", r"bg-stone-50/50"),
    (r"bg-slate-850/30", r"bg-stone-50/30"),
    (r"bg-slate-850", r"bg-stone-50"),
    (r"bg-slate-800/80", r"bg-stone-100/80"),
    (r"bg-slate-800/60", r"bg-stone-100/60"),
    (r"bg-slate-800/50", r"bg-stone-100/50"),
    (r"bg-slate-800/40", r"bg-stone-100/40"),
    (r"bg-slate-800/30", r"bg-stone-100/30"),
    (r"bg-slate-800", r"bg-stone-100"),
    (r"bg-slate-700", r"bg-stone-200"),
    (r"border-slate-800/80", r"border-stone-200/80"),
    (r"border-slate-800/60", r"border-stone-200/60"),
    (r"border-slate-800", r"border-stone-200"),
    (r"border-slate-700/80", r"border-stone-300/80"),
    (r"border-slate-700/70", r"border-stone-300/70"),
    (r"border-slate-700/60", r"border-stone-300/60"),
    (r"border-slate-700/50", r"border-stone-300/50"),
    (r"border-slate-700", r"border-stone-300"),
    (r"border-slate-600", r"border-stone-300"),
    (r"text-slate-100", r"text-stone-800"),
    (r"text-slate-200", r"text-stone-700"),
    (r"text-slate-300", r"text-stone-600"),
    (r"text-slate-400", r"text-stone-500"),
    (r"text-slate-500", r"text-stone-400"),
    (r"text-white", r"text-stone-900"),
    (r"hover:bg-slate-800", r"hover:bg-stone-100"),
    (r"hover:bg-slate-700", r"hover:bg-stone-200"),
    (r"hover:text-white", r"hover:text-stone-900"),
    (r"emerald-950/60", r"emerald-50"),
    (r"emerald-950/50", r"emerald-50"),
    (r"emerald-950/40", r"emerald-50"),
    (r"emerald-950/20", r"emerald-50"),
    (r"emerald-950/80", r"emerald-50"),
    (r"emerald-950", r"emerald-50"),
    (r"emerald-900/60", r"emerald-100/60"),
    (r"emerald-900", r"emerald-100"),
    (r"emerald-800/60", r"emerald-200/60"),
    (r"emerald-800/50", r"emerald-200"),
    (r"emerald-800", r"emerald-200"),
    (r"text-emerald-400", r"text-emerald-600"),
    (r"text-emerald-300", r"text-emerald-700"),
    (r"hover:text-emerald-400", r"hover:text-emerald-600"),
    (r"hover:text-emerald-300", r"hover:text-emerald-700"),
    (r"bg-emerald-400", r"bg-emerald-600"),
    (r"border-emerald-400", r"border-emerald-600"),
    (r"ring-emerald-400", r"ring-emerald-600"),
    (r"from-emerald-400", r"from-emerald-600"),
    (r"to-emerald-400", r"to-emerald-600"),
    (r"emerald-400", r"emerald-600"),
    (r"emerald-300", r"emerald-700"),
    (r"rose-950/50", r"rose-50"),
    (r"rose-950/40", r"rose-50"),
    (r"rose-950/30", r"rose-50"),
    (r"rose-950", r"rose-50"),
    (r"rose-900/40", r"rose-100/40"),
    (r"rose-800/60", r"rose-200/60"),
    (r"rose-800", r"rose-200"),
    (r"rose-400", r"rose-600"),
    (r"rose-300", r"rose-700"),
    (r"amber-950/60", r"amber-50"),
    (r"amber-950/40", r"amber-50"),
    (r"amber-800/60", r"amber-200/60"),
    (r"amber-800/50", r"amber-200"),
    (r"amber-800", r"amber-200"),
    (r"text-amber-400", r"text-amber-600"),
    (r"text-amber-300", r"text-amber-700"),
    (r"cyan-950/60", r"sky-50"),
    (r"cyan-800/50", r"sky-200"),
    (r"cyan-400", r"sky-600"),
    (r"purple-950/60", r"violet-50"),
]

def replace_shapes(content):
    # change rounded-lg or rounded-md on cards/containers to rounded-2xl
    # change rounded-lg on buttons to rounded-full
    # We can use regex to replace rounded-md and rounded-lg conditionally or globally, but since buttons and cards have different replacements, let's look at tags.
    # Actually, the user says:
    # 3. Change any rounded-lg or rounded-md on cards/containers to rounded-2xl
    # 4. Change any rounded-lg on buttons to rounded-full
    # Let's replace button rounded-lg and rounded-md with rounded-full
    # and all other rounded-lg/rounded-md with rounded-2xl
    
    # We can do this roughly by looking for '<button' or '<Button' and changing inside it.
    
    # Let's do a simple line-by-line replacement.
    lines = content.split('\n')
    new_lines = []
    in_button = False
    
    for line in lines:
        if '<button' in line or '<Button' in line:
            in_button = True
        
        if in_button:
            line = re.sub(r'\brounded-lg\b', 'rounded-full', line)
            line = re.sub(r'\brounded-md\b', 'rounded-full', line)
        else:
            line = re.sub(r'\brounded-lg\b', 'rounded-2xl', line)
            line = re.sub(r'\brounded-md\b', 'rounded-2xl', line)
        
        # Check if button tag closes
        if '</button>' in line or '</Button>' in line or '/>' in line and in_button and ('<button' in line or '<Button' in line):
            # rudimentary check for self closing or closing on same line
            in_button = False
        elif '>' in line and in_button:
            # tag opened and closed
            # but wait, it could be a multi-line button where `>` is on another line
            in_button = False
            
        new_lines.append(line)
        
    return '\n'.join(new_lines)


for filepath in files_to_modify:
    if not os.path.exists(filepath):
        print(f"Not found: {filepath}")
        continue
    with open(filepath, 'r') as f:
        content = f.read()
    
    for old, new in color_mapping:
        content = re.sub(r'\b' + old.replace('/', r'/') + r'\b', new, content)
        
    content = replace_shapes(content)
    
    with open(filepath, 'w') as f:
        f.write(content)
        
    print(f"Updated {filepath}")

