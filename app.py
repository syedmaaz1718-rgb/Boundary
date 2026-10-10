import os,json,sqlite3,secrets,threading
from pathlib import Path
import joblib
from flask import Flask,request,jsonify,send_from_directory,session,abort,Response
from engine import predict
ROOT=Path(__file__).parent;app=Flask(__name__,static_folder='frontend',static_url_path='/assets')
app.secret_key=os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(MAX_CONTENT_LENGTH=64*1024,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE')=='1')
if os.environ.get('COOKIE_SECURE')=='1':  # behind Render's HTTPS proxy: trust its scheme/host headers (needed for the Origin check)
 from werkzeug.middleware.proxy_fix import ProxyFix
 app.wsgi_app=ProxyFix(app.wsgi_app,x_for=1,x_proto=1,x_host=1)
model=joblib.load(ROOT/'models/chase.joblib');lock=threading.Lock()

def db():
 c=sqlite3.connect(ROOT/'data/boundary.sqlite');c.row_factory=sqlite3.Row;return c

def rows(sql,args=()):
 with db() as c:return [dict(r) for r in c.execute(sql,args)]

def one(sql,args=()):
 r=rows(sql,args);return r[0] if r else None

with db() as c:c.execute('CREATE TABLE IF NOT EXISTS scenarios(id INTEGER PRIMARY KEY,owner TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP)')

@app.before_request
def guard():
 if 'owner' not in session:session['owner']=secrets.token_hex(24);session['csrf']=secrets.token_hex(24)
 if request.method in ['POST','DELETE']:
  if request.headers.get('X-CSRF-Token')!=session['csrf']:abort(403)
  origin=request.headers.get('Origin')
  if origin and origin.rstrip('/')!=request.host_url.rstrip('/'):abort(403)

@app.after_request
def headers(resp):
 resp.headers['X-Content-Type-Options']='nosniff';resp.headers['X-Frame-Options']='DENY';resp.headers['Referrer-Policy']='same-origin'
 resp.headers['Content-Security-Policy']="default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'"
 if request.path.startswith('/api/'):resp.headers['Cache-Control']='no-store'
 return resp

@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(413)
def error(e):return jsonify(error=e.description),e.code

@app.get('/healthz')
def healthz():return {'ok':True}

@app.get('/api/meta')
def meta():
 return jsonify(csrf=session['csrf'],seasons=rows('SELECT season,COUNT(*) matches FROM matches GROUP BY season ORDER BY season DESC'),teams=rows('SELECT team1 name FROM matches UNION SELECT team2 FROM matches ORDER BY name'),venues=rows('SELECT venue name,COUNT(*) matches FROM matches GROUP BY venue ORDER BY matches DESC'),manifest=json.load(open(ROOT/'data/manifest.json')))

@app.get('/api/matches')
def matches():
 season=request.args.get('season','');q=request.args.get('q','')[:100];params=[];where=[]
 if season:where.append('season=?');params.append(season)
 if q:where.append('(team1 LIKE ? OR team2 LIKE ? OR venue LIKE ?)');params.extend(['%'+q+'%']*3)
 sql='SELECT * FROM matches'+(' WHERE '+' AND '.join(where) if where else '')+' ORDER BY date DESC,id DESC LIMIT 200'
 return jsonify(rows(sql,params))

@app.get('/api/match/<mid>')
def match(mid):
 m=one('SELECT * FROM matches WHERE id=?',(mid,))
 if not m:abort(404)
 return jsonify(match=m,balls=rows('SELECT * FROM balls WHERE match_id=? ORDER BY seq',(mid,)),players=rows('SELECT * FROM player_match WHERE match_id=? ORDER BY runs DESC',(mid,)))

def state(body):
 keys=['score','wickets','legal','target'];v={}
 for k in keys:
  if type(body.get(k)) is not int:abort(400,description='Use whole-number score, wickets, balls and target.')
  v[k]=body[k]
 if not(0<=v['score']<=400 and 0<=v['wickets']<=10 and 0<=v['legal']<=120 and 1<=v['target']<=400):abort(400,description='State outside accepted T20 bounds.')
 return v

@app.post('/api/predict')
def prediction():
 b=request.get_json(silent=True) or {};v=state(b)
 with lock:p=predict(model,**v)
 return jsonify(probability=p,features=v,caution='State-only standard 20-over chase estimate. Counterfactual association, not causal effect.',outside_training=v['target']<80 or v['target']>270)

@app.get('/api/players')
def players():
 season=request.args.get('season','');q=request.args.get('q','')[:100];where=['p.player LIKE ?'];args=['%'+q+'%']
 if season:where.append('m.season=?');args.append(season)
 return jsonify(rows('''SELECT p.player,COUNT(*) matches,SUM(runs) runs,SUM(balls) balls,SUM(fours) fours,SUM(sixes) sixes,SUM(p.wickets) wickets,SUM(legal_bowled) legal_bowled,SUM(conceded) conceded,SUM(bat_impact) bat_impact,SUM(bowl_impact) bowl_impact,SUM(bat_impact+bowl_impact) impact,SUM(m.eligible) modeled_matches FROM player_match p JOIN matches m ON m.id=p.match_id WHERE '''+' AND '.join(where)+' GROUP BY p.player ORDER BY impact DESC LIMIT 500',args))

@app.get('/api/player')
def player():
 n=request.args.get('name','');r=rows('SELECT p.*,m.date,m.season,m.team1,m.team2,m.eligible FROM player_match p JOIN matches m ON m.id=p.match_id WHERE p.player=? ORDER BY m.date DESC',(n,))
 if not r:abort(404)
 return jsonify(name=n,innings=r)

@app.get('/api/aggregate')
def aggregate():
 kind=request.args.get('kind');v=request.args.get('value','');where='1=1';args=[]
 if kind=='team':where='(team1=? OR team2=?)';args=[v,v]
 elif kind=='venue':where='venue=?';args=[v]
 elif kind=='season':where='season=?';args=[v]
 elif kind=='h2h':where='((team1=? AND team2=?) OR (team1=? AND team2=?))';t=request.args.get('other','');args=[v,t,t,v]
 else:abort(400)
 ms=rows('SELECT * FROM matches WHERE '+where+' ORDER BY date DESC',args)
 wins={};seasons={}
 for m in ms:
  if m['winner']:wins[m['winner']]=wins.get(m['winner'],0)+1
  seasons[m['season']]=seasons.get(m['season'],0)+1
 return jsonify(matches=ms,wins=wins,seasons=seasons,average_first_score=sum(m['first_score'] for m in ms)/len(ms) if ms else None,chase_wins=sum(m['winner']==m['batting'] for m in ms),decided=sum(bool(m['winner']) for m in ms))

@app.get('/api/evaluation')
def evaluation():return jsonify(json.load(open(ROOT/'models/evaluation.json')))

@app.route('/api/scenarios',methods=['GET','POST'])
def scenarios():
 if request.method=='GET':return jsonify(rows('SELECT id,title,body,created FROM scenarios WHERE owner=? ORDER BY id DESC',(session['owner'],)))
 b=request.get_json(silent=True) or {};v=state(b);title=str(b.get('title',''))[:100].strip()
 if not title:abort(400,description='Give the scenario a title.')
 with db() as c:
  if c.execute('SELECT COUNT(*) FROM scenarios WHERE owner=?',(session['owner'],)).fetchone()[0]>=100:abort(400,description='Notebook limit: 100 scenarios.')
  c.execute('INSERT INTO scenarios(owner,title,body) VALUES(?,?,?)',(session['owner'],title,json.dumps(v)))
 return jsonify(saved=True),201

@app.delete('/api/scenarios/<int:sid>')
def delete(sid):
 with db() as c:r=c.execute('DELETE FROM scenarios WHERE owner=? AND id=?',(session['owner'],sid))
 if r.rowcount==0:abort(404)
 return jsonify(deleted=True)

@app.get('/api/export/<mid>')
def export(mid):
 import csv,io
 m=one('SELECT id FROM matches WHERE id=?',(mid,))
 if not m:abort(404)
 rs=rows('SELECT * FROM balls WHERE match_id=? ORDER BY seq',(mid,));f=io.StringIO();w=csv.DictWriter(f,fieldnames=rs[0].keys() if rs else ['match_id']);w.writeheader();w.writerows(rs)
 return Response(f.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename="boundary-{mid}.csv"'})

@app.get('/')
@app.get('/<path:path>')
def frontend(path=''):
 if path.startswith('api/'):abort(404)
 return send_from_directory(ROOT/'frontend','index.html')

if __name__=='__main__':app.run(host='127.0.0.1',port=int(os.environ.get('PORT','8000')))
