"""Analyse van TNO-warmteprofielen (Warmteprofielengenerator): dagritme, piek en vergelijking met het eigen model."""
import json, os, sys
import numpy as np, pandas as pd
import middelsee as m
D=os.path.join(m.ROOT,'data/energynl')
def laad(job):
    r=json.load(open(os.path.join(D,'res%d.json'%job)))
    u=r['user_job_results']; t=u['timeseries']
    h=np.array([x['value'] for x in t['heat_profile']],float); T=np.array([x['value'] for x in t['outside_temperature']],float)
    return r['user_job'],u,h,T
def vorm(h,T,year):
    idx=pd.date_range('%d-12-31 23:00'%(year-1),periods=8760,freq='h')  # eerste waarde van de generator: lokale middernacht = 23:00 UT
    loc=idx.tz_localize('UTC').tz_convert('Europe/Amsterdam')
    d=pd.DataFrame({'h':h,'T':T,'u':loc.hour,'dag':np.arange(8760)//24})
    dg=d.groupby('dag').agg(h=('h','mean'),T=('T','mean'))
    out={}
    for naam,sel in (('koud (<0 C)',dg['T']<0),('winter (0-6 C)',(dg['T']>=0)&(dg['T']<6))):
        x=d[d.dag.isin(dg.index[sel])]
        out[naam]=(x.groupby('u').h.mean()/x.h.mean())
    return pd.DataFrame(out),dg,int(np.argmax(h)),idx
if __name__=='__main__':
    job=int(sys.argv[1]); uj,u,h,T=laad(job)
    n=[x['number'] for x in u['stats']['building_number_stats'] if x['description']=='nr_of_residential_building_units'][0]
    print(uj['neighbourhood'],uj['reference_year'],uj['reference_station'],'woningen',n)
    print('eenheid: som %.3e, max %.3e, power_stats %s'%(h.sum(),h.max(),u['power_stats']))
    print('bouwjaar',u['stats']['building_year_class_distribution'])
    sc=1e-6 if h.max()>1e5 else (1e-3 if h.max()>1e2 else 1.0)
    print('per woning: jaar %.1f GJ, piek %.2f kW; piek/gemiddelde %.1f'%(h.sum()*sc*3.6/n,h.max()*sc*1e3/n,h.max()/h.mean()))
    v,dg,i,idx=vorm(h,T,uj['reference_year'])
    print('piekuur',idx[i],'T %.1f'%T[i]); print(v.round(2).T.to_string())
    print('verhouding max dag-uur / etmaalgemiddelde',v.max().round(2).to_dict(),'min',v.min().round(2).to_dict())
    j=m.Jaar(2017)
    print('eigen model 2017: piek/gemiddelde sh_won %.1f; sh_won + tapwater %.1f'%(j.sh_won.max()/j.sh_won.mean(),(j.sh_won+j.dhw_won).max()/(j.sh_won+j.dhw_won).mean()))
    k=m._uur(uj['reference_year'],m._knmi())['T'].values
    print('T Eelde tegen Leeuwarden: corr %.3f, gem %.1f/%.1f, min %.1f/%.1f'%(np.corrcoef(T,k)[0,1],T.mean(),k.mean(),T.min(),k.min()))
    v.to_csv(os.path.join(m.ROOT,'uitvoer/wpg_dagvorm_job%d.csv'%job))
