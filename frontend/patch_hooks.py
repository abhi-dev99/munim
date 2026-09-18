import os

filepath = 'd:/hackathob/kleos-4.0/frontend/src/app/components/SupplierHealth.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The hooks to move
hooks_to_move = """  const dragItem = useRef(null);
  const dragOverItem = useRef(null);
  const [cardOrder, setCardOrder] = useState(["ALL", "GOOD", "RISK", "CRITICAL"]);

"""

# Remove them from the bottom
content = content.replace(hooks_to_move, "")

# Add them to the top
target = 'const [activeSupplier, setActiveSupplier] = useState(null); // supplier overlay'
replacement = target + "\n\n" + hooks_to_move.rstrip()

content = content.replace(target, replacement)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Hooks moved successfully.")
