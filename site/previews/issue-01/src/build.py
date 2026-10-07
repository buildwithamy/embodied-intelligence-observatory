import re,pathlib
s=pathlib.Path('/home/claude/issue01/v3/page.html').read_text(encoding='utf-8')
art=pathlib.Path('/home/claude/issue01/art')
out=re.sub(r'\{\{svg:([\w-]+)\}\}',lambda m:re.sub(r'<\?xml[^>]*\?>','',(art/(m.group(1)+'.svg')).read_text(encoding='utf-8')).strip(),s)
assert '{{' not in out
pathlib.Path('/home/claude/issue01/v3/index.html').write_text(out,encoding='utf-8')
print('built',len(out))
