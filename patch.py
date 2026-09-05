import os
import re

directory = r'd:\hackathob\kleos-4.0\frontend\src\app'

for root, dirs, files in os.walk(directory):
    for file in files:
        if not file.endswith('.js'):
            continue
            
        filepath = os.path.join(root, file)
        
        # Skip the utility file itself and the main login page
        if 'utils' in filepath or filepath.endswith('app\\page.js'):
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'fetch(' not in content:
            continue
            
        # Add import
        import_stmt = 'import { authFetch } from "@/app/utils/api";\n'
        if '"use client";' in content:
            content = content.replace('"use client";', '"use client";\n' + import_stmt)
        elif "'use client';" in content:
            content = content.replace("'use client';", "'use client';\n" + import_stmt)
        else:
            content = import_stmt + content
            
        content = re.sub(r'\bfetch\(', 'authFetch(', content)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
print('Patched successfully.')
