import pytest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import app,db
from engine import predict
import joblib
@pytest.fixture
def client():return app.test_client()
def auth(c):return {'X-CSRF-Token':c.get('/api/meta').json['csrf']}
def test_counts(client):
 m=client.get('/api/evaluation').json;assert m['archive_matches']==1243;assert m['test']['matches']==138;assert m['metrics']['brier']<m['baseline']['brier']
def test_match(client):
 d=client.get('/api/match/1535465').json;assert d['match']['target']==156;assert all(b['prob'] is None or 0<=b['prob']<=1 for b in d['balls'])
def test_legal(client):
 bs=client.get('/api/match/1535465').json['balls'];assert bs[-1]['legal']<=120;assert bs[-1]['score']>=156;assert bs[-1]['prob']==1
def test_missing(client):assert client.get('/api/match/nothing').status_code==404
def test_predict(client):
 r=client.post('/api/predict',headers=auth(client),json=dict(score=116,wickets=4,legal=72,target=156));assert r.status_code==200;assert 0<=r.json['probability']<=1
@pytest.mark.parametrize('s,w,b,t,p',[(156,4,72,156,1),(0,10,72,156,0),(155,4,120,156,0),(157,10,120,156,1)])
def test_terminal(client,s,w,b,t,p):assert client.post('/api/predict',headers=auth(client),json=dict(score=s,wickets=w,legal=b,target=t)).json['probability']==p
@pytest.mark.parametrize('body',[dict(score=-1,wickets=1,legal=1,target=156),dict(score=1,wickets=11,legal=1,target=156),dict(score=1,wickets=1,legal=121,target=156),dict(score=1,wickets=1,legal=1,target=0),dict(score=1.5,wickets=1,legal=1,target=156),{}])
def test_invalid(client,body):assert client.post('/api/predict',headers=auth(client),json=body).status_code==400
def test_csrf(client):assert client.post('/api/predict',json={}).status_code==403
def test_cross_origin(client):assert client.post('/api/predict',headers={**auth(client),'Origin':'https://bad.example'},json={}).status_code==403
def test_isolation(client):
 v=dict(score=116,wickets=4,legal=72,target=156,title='test only');assert client.post('/api/scenarios',headers=auth(client),json=v).status_code==201
 ns=client.get('/api/scenarios').json;sid=ns[0]['id'];other=app.test_client();h=auth(other);assert other.get('/api/scenarios').json==[];assert other.delete('/api/scenarios/'+str(sid),headers=h).status_code==404;assert client.delete('/api/scenarios/'+str(sid),headers=auth(client)).status_code==200
def test_players(client):
 p=client.get('/api/players?q=Kohli').json;assert any(x['player']=='V Kohli' and x['runs']>0 for x in p)
@pytest.mark.parametrize('kind,value',[('team','Chennai Super Kings'),('venue','Wankhede Stadium'),('season','2026'),('h2h','Chennai Super Kings')])
def test_aggregate(client,kind,value):assert client.get('/api/aggregate',query_string=dict(kind=kind,value=value,other='Mumbai Indians')).status_code==200
def test_export(client):
 r=client.get('/api/export/1535465');assert r.status_code==200;assert b'before_prob' in r.data
def test_no_predictions_excluded(client):
 with db() as c:assert c.execute('SELECT COUNT(*) FROM balls b JOIN matches m ON m.id=b.match_id WHERE m.eligible=0 AND b.prob IS NOT NULL').fetchone()[0]==0
