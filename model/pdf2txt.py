import pypdf,sys,glob,os,zipfile,re
for f in sorted(glob.glob(sys.argv[1]+'/*')):
    if f.endswith('.txt'): continue
    head=open(f,'rb').read(4)
    if head==b'PK\x03\x04':
        x=zipfile.ZipFile(f).read('word/document.xml').decode('utf8')
        x=re.sub(r'</w:p>','\n',x); x=re.sub(r'<[^>]+>','',x)
        open(f+'.txt','w').write(x); print('docx',os.path.basename(f),len(x)); continue
    if head!=b'%PDF': print('geen pdf',os.path.basename(f)); continue
    try:
        r=pypdf.PdfReader(f); t='\n'.join(f'--- p{i+1} ---\n'+(p.extract_text() or '') for i,p in enumerate(r.pages))
        open(f+'.txt','w').write(t); print(os.path.basename(f),len(r.pages),len(t))
    except Exception as e: print('fout',os.path.basename(f),e)
