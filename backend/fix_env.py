with open('.env', 'rb') as f:
    content = f.read()

content = content.replace(b'\x00', b'')

with open('.env', 'wb') as f:
    f.write(content)
