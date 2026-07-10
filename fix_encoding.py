import os

replacements = [
    ('\u2013', '-'),
    ('\u2014', '--'),
    ('\u2022', '*'),
    ('\u2019', "'"),
    ('\u201c', '"'),
    ('\u201d', '"'),
    ('\u2713', '[OK]'),
    ('\u2705', '[DONE]'),
    ('\u274c', '[X]'),
    ('\u26a0', '[!]'),
]

fixed_files = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.streamlit', 'node_modules']]
    for fname in files:
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(root, fname)
        try:
            content = open(fpath, 'r', encoding='utf-8').read()
            new_content = content
            for bad, good in replacements:
                new_content = new_content.replace(bad, good)
            if new_content != content:
                open(fpath, 'w', encoding='utf-8').write(new_content)
                fixed_files.append(fpath)
        except Exception as e:
            print(f'Error on {fpath}: {e}')

if fixed_files:
    print('Fixed files:')
    for f in fixed_files:
        print(f'  {f}')
else:
    print('All clean - no non-ASCII found in print statements!')
print('Sweep complete.')
