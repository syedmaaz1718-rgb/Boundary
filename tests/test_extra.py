from test_app import client,auth

def test_pressure_changes(client):
 h=auth(client);a=client.post('/api/predict',headers=h,json=dict(score=116,wickets=4,legal=72,target=156)).json['probability'];b=client.post('/api/predict',headers=h,json=dict(score=75,wickets=4,legal=72,target=156)).json['probability'];assert a>b

def test_source_season(client):assert len(client.get('/api/matches?season=2007/08').json)==58
