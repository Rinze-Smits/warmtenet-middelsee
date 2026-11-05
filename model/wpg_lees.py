import json,subprocess,sys
A='https://hlc-api.warmteprofielengenerator.nl'
def get(p):
    return json.loads(subprocess.run(['curl','-sS','-m','40',A+p],capture_output=True,text=True).stdout)
w=json.load(open('wy.json'))['weather_year_infos']
print('weerjaren:',[(x['id'],x['year'],x['station']) for x in w if 'eeuw' in x['station'] or x['year'] in (2012,2010,2017)][:30], 'stations',sorted({x['station'] for x in w}))
d=json.load(open('wijken.json'))
print(list(d['features'][0]['properties'].items())[:6] if d.get('features') else d)
for f in d['features']:
    p=f['properties']; code=p.get('code') or p.get('district_code'); nm=p.get('name') or p.get('naam')
    if any(k in (nm or '') for k in ['Zuidlanden','Middelsee','Goutum','Wirdum','Techum','Zuid']):
        print('WIJK',code,nm)
        b=get('/region_data/neighbourhood/shape?district_code=%s'%code)
        for g in b.get('features',[]):
            q=g['properties']; c=q.get('code') or q.get('neighbourhood_code'); n=q.get('name') or q.get('naam')
            j=get('/user_jobs/?neighbourhood_code=%s'%c).get('user_jobs',[])
            print('   ',c,n,'jobs',len(j),[(x['id'],x.get('reference_year'),x.get('finished') is not None,x.get('enabled_installation_types')) for x in j][-3:])
