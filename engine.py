"""Anonymous state-only chase model. No identity or final result features."""
import numpy as np

def features(score,wickets,legal,target):
 left=max(0,120-legal);need=max(0,target-score);wi=max(0,10-wickets)
 return [need,left,wi,target,need*6/max(left,1),score*6/max(legal,1),need/max(left,1),need/max(wi,1)]

def estimate(model,X):
 raw=np.clip(model['classifier'].predict_proba(np.asarray(X))[:,1],1e-5,1-1e-5)
 return model['calibrator'].predict_proba(np.log(raw/(1-raw)).reshape(-1,1))[:,1]

def predict(model,score,wickets,legal,target):
 if score>=target:return 1.
 if wickets>=10 or legal>=120:return 0.
 return float(estimate(model,[features(score,wickets,legal,target)])[0])
