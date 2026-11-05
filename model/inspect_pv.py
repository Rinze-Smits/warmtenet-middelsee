import json,sys,glob,os
import pandas as pd
for f in sorted(glob.glob(sys.argv[1]+'/pv_*.json')):
    j=json.load(open(f)); m=j['inputs']['mounting_system']['fixed']; d=pd.DataFrame(j['outputs']['hourly'])
    d['t']=pd.to_datetime(d['time'],format='%Y%m%d:%H%M'); s=d.set_index('t')['P']/1000
    y=s.groupby(s.index.year).sum()
    print(os.path.basename(f),j['inputs']['meteo_data']['radiation_db'],'slope',m['slope']['value'],'az',m['azimuth']['value'],'gem kWh/kWp %.0f min %.0f max %.0f piek %.2f'%(y.mean(),y.min(),y.max(),s.max()), 'minuut',d['t'].dt.minute.iloc[0])
