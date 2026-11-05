import json,sys
s=json.load(open(sys.argv[1]))
print(s.get('info'),s.get('host'),s.get('basePath'),'security',s.get('security'),s.get('securityDefinitions'))
for p,v in s['paths'].items():
    for m,o in v.items():
        if isinstance(o,dict): print(m.upper(),p,'|',(o.get('summary') or o.get('description') or '')[:110].replace('\n',' '),'| params:',[ (x.get('name'),x.get('in')) for x in o.get('parameters',[])][:10])
d=s.get('definitions') or s.get('components',{}).get('schemas',{})
for k,v in d.items():
    pr=v.get('properties',{})
    print('DEF',k,'req',v.get('required'),{a:(b.get('type'),b.get('default')) for a,b in list(pr.items())[:40]})
