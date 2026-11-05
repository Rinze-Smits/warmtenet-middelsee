import re,sys,html
for f in sys.argv[1:]:
    s=open(f,errors='ignore').read()
    links=sorted(set(re.findall(r'href="([^"]+)"',s)))
    s=re.sub(r'(?is)<(script|style|svg|nav|footer).*?</\1>',' ',s); s=re.sub(r'<[^>]+>','\n',s); s=html.unescape(s)
    t='\n'.join(l.strip() for l in s.split('\n') if l.strip())
    print('=====',f,len(t)); print(t[:6500]); print('--- links'); print('\n'.join(l for l in links if 'tools/' in l or 'api' in l.lower() or 'github' in l or 'pdf' in l or 'docs' in l)[:3500])
