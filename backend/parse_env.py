import os
import yaml

env_file = '.env'
env_dict = {}
with open(env_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            key, val = line.split('=', 1)
            key = key.strip()
            val = val.strip().strip('\'\"')
            env_dict[key] = val

with open('env.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(env_dict, f, default_flow_style=False)

print('Successfully created env.yaml')
