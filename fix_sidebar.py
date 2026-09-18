import os
filepath = 'frontend/src/app/components/Sidebar.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract navItems block
navItems_start = content.find('  const navItems = [')
navItems_end = content.find('  ];\n', navItems_start) + 5

navItems_block = content[navItems_start:navItems_end]

# Remove it from the original location
content = content[:navItems_start] + content[navItems_end:]

# Insert it right before `const visibleNavItems =`
target_index = content.find('  // Default nav items are defined as navItems above.')
content = content[:target_index] + navItems_block + '\n' + content[target_index:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed navItems initialization order.")
