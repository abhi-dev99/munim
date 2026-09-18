import os
filepath = 'frontend/src/app/components/Sidebar.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add usePathname import
if 'usePathname' not in content:
    content = content.replace('import { useRouter } from "next/navigation";', 'import { useRouter, usePathname } from "next/navigation";')

# 2. Add pathname const
if 'const pathname = usePathname();' not in content:
    content = content.replace('const router = useRouter();', 'const router = useRouter();\n  const pathname = usePathname();')

# 3. Update Profile rendering logic to use pathname for active styling
old_profile_button = """className="flex items-center gap-3 px-3 py-2.5 text-gray-600 hover:text-gray-900 hover:bg-gray-50 
rounded-lg transition-colors w-full text-sm font-semibold\""""
old_profile_button2 = 'className="flex items-center gap-3 px-3 py-2.5 text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-colors w-full text-sm font-semibold"'

new_profile_button = 'className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors w-full text-sm font-semibold ${pathname === "/dashboard/profile" ? "bg-emerald-50 text-emerald-600 font-bold" : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"}`}'

if old_profile_button2 in content:
    content = content.replace(old_profile_button2, new_profile_button)
elif old_profile_button in content:
    content = content.replace(old_profile_button, new_profile_button)
else:
    # If standard multiline failed, let's just do a regex sub or broader replace
    import re
    content = re.sub(r'className="flex items-center gap-3 px-3 py-2\.5 text-gray-600 hover:text-gray-900 hover:bg-gray-50\s*rounded-lg transition-colors w-full text-sm font-semibold"', new_profile_button, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added active state to profile tab in Sidebar.js")
