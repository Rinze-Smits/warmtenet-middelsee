"""Start een eigen run; de resultaatlink gaat naar het adres in WPG_EMAIL. Gebruik: wpg_start.py <naam> <jaar_id> <vermogen_kW> <installatietype-json>"""
import json,subprocess,sys,os
A='https://hlc-api.warmteprofielengenerator.nl'
D=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data/energynl/')
naam,yid,pw,inst=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),json.loads(sys.argv[4])
w=json.load(open(D+'wkt_BU00807302.json'))
p=dict(wkt=w['wkt'],reference_year_id=yid,installed_power=pw,non_houses=sys.argv[5],extra_information=sys.argv[6],neighbourhood_code='BU00807302',cooling_enabled=False,
       sunshades_enabled=True,open_windows_enabled=True,user_email=os.environ['WPG_EMAIL'],installation_data=inst,random_seed='middelsee1',setpoint_source=sys.argv[7])
r=subprocess.run(['curl','-sS','-m','90','-X','POST',A+'/compute/wkt','-H','Content-Type: application/json','-d',json.dumps(p),'-w','\nHTTP %{http_code}'],capture_output=True,text=True)
print(naam,r.stdout[:400],r.stderr[:200])
open(D+'runs.log','a').write(naam+' '+r.stdout.replace('\n',' ')[:200]+'\n')
