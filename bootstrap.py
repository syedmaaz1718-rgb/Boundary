"""Reproducible Cricsheet ingestion, temporal evaluation and SQLite build."""
import os,sys,json,zipfile,urllib.request,hashlib,sqlite3,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np,joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss,brier_score_loss,roc_auc_score,accuracy_score
from threadpoolctl import threadpool_limits
from engine import features,estimate
ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://cricsheet.org/downloads/ipl_json.zip'

def bootstrap(archive=None):
 (ROOT/'data').mkdir(exist_ok=True);(ROOT/'models').mkdir(exist_ok=True)
 if not archive:
  archive=ROOT/'data/ipl-source.zip';urllib.request.urlretrieve(SOURCE,archive)
 z=zipfile.ZipFile(archive);db=sqlite3.connect(ROOT/'data/boundary.sqlite');db.executescript('''
 DROP TABLE IF EXISTS matches;DROP TABLE IF EXISTS balls;DROP TABLE IF EXISTS player_match;
 CREATE TABLE matches(id TEXT PRIMARY KEY,date TEXT,season TEXT,venue TEXT,city TEXT,team1 TEXT,team2 TEXT,batting TEXT,bowling TEXT,winner TEXT,target INT,first_score INT,chase_score INT,chase_wickets INT,eligible INT,exclusion TEXT,stage TEXT,toss TEXT);
 CREATE TABLE balls(match_id TEXT,seq INT,legal INT,label TEXT,batter TEXT,bowler TEXT,non_striker TEXT,runs INT,batter_runs INT,extras INT,wicket INT,score INT,wickets INT,before_score INT,before_wickets INT,before_legal INT,prob REAL,before_prob REAL,delta REAL,PRIMARY KEY(match_id,seq));
 CREATE TABLE player_match(match_id TEXT,player TEXT,team TEXT,runs INT,balls INT,fours INT,sixes INT,wickets INT,legal_bowled INT,conceded INT,bat_impact REAL DEFAULT 0,bowl_impact REAL DEFAULT 0,PRIMARY KEY(match_id,player));
 CREATE INDEX idx_season ON matches(season);CREATE INDEX idx_player ON player_match(player);
 ''')
 matches=[];ballrows=[];credits={};stats=[];X=[];Y=[];dates=[];ids=[];skipped={};names=sorted(n for n in z.namelist() if n.endswith('.json'))
 for name in names:
  m=json.loads(z.read(name));info=m['info'];innings=m.get('innings',[]);mid=Path(name).stem
  teams=info['teams'];date=info['dates'][0];out=info.get('outcome',{});win=out.get('winner','');reason=''
  if len(innings)<2:reason='Missing completed chase'
  elif any(i.get('super_over') for i in innings) or len(innings)!=2:reason='Super-over / multiple innings'
  elif out.get('method') or any(i.get('target',{}).get('overs',20)!=20 for i in innings):reason='Adjusted target / shortened match'
  elif info.get('overs',20)!=20 or info.get('balls_per_over',6)!=6:reason='Non-standard innings length'
  elif not win or out.get('result'):reason='Tie / no result'
  first=innings[0] if innings else {}; chase=innings[1] if len(innings)>1 else {};fscore=sum(d['runs']['total'] for o in first.get('overs',[]) for d in o['deliveries']);target=fscore+1
  bat=chase.get('team','');bowl=next((t for t in teams if t!=bat),teams[0]);score=wickets=legal=0;seq=0
  pm={}
  def person(n,t):
   if n not in pm:pm[n]=dict(team=t,runs=0,balls=0,fours=0,sixes=0,wickets=0,legal_bowled=0,conceded=0)
   return pm[n]
  for t,players in info.get('players',{}).items():
   for n in players:person(n,t)
  for inn in innings:
   iteam=inn['team'];opponent=next(t for t in teams if t!=iteam)
   for o in inn.get('overs',[]):
    for d in o['deliveries']:
     e=d.get('extras',{});islegal=not(e.get('wides',0) or e.get('noballs',0));b=person(d['batter'],iteam);p=person(d['bowler'],opponent)
     b['runs']+=d['runs']['batter'];b['balls']+=int(not e.get('wides',0));b['fours']+=int(d['runs']['batter']==4);b['sixes']+=int(d['runs']['batter']==6)
     p['legal_bowled']+=int(islegal);p['conceded']+=d['runs']['total']-e.get('byes',0)-e.get('legbyes',0)
     p['wickets']+=sum(w['kind'] not in ['run out','retired hurt','obstructing the field','retired out'] for w in d.get('wickets',[]))
  for o in chase.get('overs',[]):
   for d in o['deliveries']:
    e=d.get('extras',{});islegal=not(e.get('wides',0) or e.get('noballs',0));wc=sum(w['kind']!='retired hurt' for w in d.get('wickets',[]));pre=(score,wickets,legal);score+=d['runs']['total'];wickets+=wc;legal+=int(islegal);seq+=1
    credits[(mid,seq)]=(not d.get('wickets') or all(w['player_out']==d['batter'] for w in d['wickets']),all(w['kind'] not in ['run out','retired hurt','obstructing the field','retired out'] for w in d.get('wickets',[])))
    ballrows.append([mid,seq,legal,d.get('actual_delivery',f"{o['over']}.{seq}"),d['batter'],d['bowler'],d['non_striker'],d['runs']['total'],d['runs']['batter'],d['runs']['extras'],wc,score,wickets,*pre,None,None,None])
    if not reason and pre[2]<120 and pre[1]<10 and pre[0]<target:
     X.append(features(pre[0],pre[1],pre[2],target));Y.append(int(win==bat));dates.append(date);ids.append(mid)
  for n,s in pm.items():stats.append([mid,n,s['team'],s['runs'],s['balls'],s['fours'],s['sixes'],s['wickets'],s['legal_bowled'],s['conceded'],0.,0.])
  if not reason and (legal>120 or wickets>10):reason='Invalid standard chase'
  if reason:skipped[reason]=skipped.get(reason,0)+1
  matches.append([mid,date,str(info.get('season',date[:4])),info.get('venue','Unknown'),info.get('city',''),*teams,bat,bowl,win,target,fscore,score,wickets,int(not reason),reason,info.get('event',{}).get('stage',''),f"{info.get('toss',{}).get('winner','')} chose to {info.get('toss',{}).get('decision','')}"])
 print('Ingested',len(matches),'matches /',len(ballrows),'chase deliveries',flush=True)
 # Split by entire matches, by date. No random ball-level leakage.
 X=np.asarray(X);Y=np.asarray(Y);dates=np.asarray(dates);ids=np.asarray(ids)
 tr=dates<'2024-01-01';ca=(dates>='2024-01-01')&(dates<'2025-01-01');te=dates>='2025-01-01'
 with threadpool_limits(limits=2):
  clf=HistGradientBoostingClassifier(max_iter=130,max_leaf_nodes=15,min_samples_leaf=100,l2_regularization=4,learning_rate=.075,random_state=42).fit(X[tr],Y[tr])
  raw=np.clip(clf.predict_proba(X[ca])[:,1],1e-5,1-1e-5);cal=LogisticRegression(C=1e3).fit(np.log(raw/(1-raw)).reshape(-1,1),Y[ca])
  raw=np.clip(clf.predict_proba(X[te])[:,1],1e-5,1-1e-5);pr=cal.predict_proba(np.log(raw/(1-raw)).reshape(-1,1))[:,1]
 model=dict(classifier=clf,calibrator=cal);joblib.dump(model,ROOT/'models/chase.joblib',compress=3)
 base=np.repeat(Y[tr].mean(),te.sum());metrics=lambda p:dict(log_loss=float(log_loss(Y[te],p)),brier=float(brier_score_loss(Y[te],p)),auc=float(roc_auc_score(Y[te],p)),accuracy=float(accuracy_score(Y[te],p>=.5)))
 bins=[]
 for lo in np.arange(0,1,.1):
  mask=(pr>=lo)&(pr<lo+.1);bins.append(dict(low=round(float(lo),1),count=int(mask.sum()),predicted=float(pr[mask].mean()) if mask.any() else None,observed=float(Y[te][mask].mean()) if mask.any() else None))
 report=dict(source=SOURCE,archive_sha256=hashlib.sha256(Path(archive).read_bytes()).hexdigest(),built_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),archive_matches=len(matches),chase_deliveries=len(ballrows),eligible_matches=sum(r[14] for r in matches),excluded=skipped,features=['runs_needed','balls_left','wickets_left','target','required_rate','current_rate','run_pressure','wickets_pressure'],train=dict(period='2008-2023',states=int(tr.sum()),matches=len(set(ids[tr]))),calibration=dict(period='2024',states=int(ca.sum()),matches=len(set(ids[ca]))),test=dict(period='2025-2026',states=int(te.sum()),matches=len(set(ids[te]))),metrics=metrics(pr),baseline=metrics(base),calibration_bins=bins)
 json.dump(report,open(ROOT/'models/evaluation.json','w'),indent=2);print(json.dumps(report,indent=2),flush=True)
 # Populate true model probability paths for all eligible chases; unavailable stays NULL.
 eligible={m[0]:m[10] for m in matches if m[14]};validrows=[r for r in ballrows if r[0] in eligible]
 with threadpool_limits(limits=2):
  before=estimate(model,np.array([features(r[13],r[14],r[15],eligible[r[0]]) for r in validrows]));after=estimate(model,np.array([features(r[11],r[12],r[2],eligible[r[0]]) for r in validrows]))
 impact={}
 for r,p,q in zip(validrows,before,after):
  target=eligible[r[0]]
  if r[11]>=target:q=1.
  elif r[12]>=10 or r[2]>=120:q=0.
  r[16]=float(q);r[17]=float(p);r[18]=float(q-p)
  # Role attribution only; exclude extras from batter credit and run-outs from bowler credit.
  if r[9]==0 and credits[(r[0],r[1])][0]:impact.setdefault((r[0],r[4]),[0.,0.])[0]+=r[18]*100
  if r[9]==0 and credits[(r[0],r[1])][1]:impact.setdefault((r[0],r[5]),[0.,0.])[1]-=r[18]*100
 # Exclude non-striker dismissals from batter attribution and non-bowler wickets from bowler attribution.
 for s in stats:s[10],s[11]=impact.get((s[0],s[1]),[0.,0.])
 db.executemany('INSERT INTO matches VALUES('+','.join('?'*18)+')',matches);db.executemany('INSERT INTO balls VALUES('+','.join('?'*19)+')',ballrows);db.executemany('INSERT INTO player_match VALUES('+','.join('?'*12)+')',stats);db.commit();db.execute('VACUUM');db.close()
 json.dump(dict(source=SOURCE,sha256=report['archive_sha256'],matches=len(matches),date_range=[min(m[1] for m in matches),max(m[1] for m in matches)]),open(ROOT/'data/manifest.json','w'),indent=2)
if __name__=='__main__':bootstrap(sys.argv[1] if len(sys.argv)>1 else None)
