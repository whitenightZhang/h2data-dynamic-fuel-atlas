"""Group-held-out corrections using only ex ante features and training hourly labels."""
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.model_selection import LeaveOneGroupOut

def resource_features(wind,pv,timestamps):
    w=np.asarray(wind,dtype=float);p=np.asarray(pv,dtype=float)
    if len(w)!=8760 or len(p)!=8760 or np.mean(w)<=0 or np.mean(p)<=0:raise ValueError('Expected positive-mean full-year resource profiles')
    profile=.5*w/w.mean()+.5*p/p.mean()
    daily=profile.reshape(365,24).mean(axis=1)
    months=np.asarray(timestamps).astype('datetime64[M]')
    monthly=np.array([profile[months==m].mean() for m in np.unique(months)])
    rolling=np.convolve(profile,np.ones(168)/168,mode='valid')
    return np.array([w.mean(),p.mean(),np.corrcoef(w,p)[0,1],daily.std()/daily.mean(),monthly.min()/profile.mean(),max(0.,1.-rolling.min()),np.maximum(1.-profile,0.).mean()])

def fit_corrections(x,yannual,yhourly,groups,train,test,alphas=(.1,1.,10.,100.)):
    train=np.asarray(train);test=np.asarray(test)
    if np.intersect1d(train,test).size:raise ValueError('Training and test indices overlap')
    if set(np.asarray(groups)[train]) & set(np.asarray(groups)[test]):raise ValueError('Macro-region leakage')
    # Only training hourly labels are accessed in this function.
    a=np.asarray(yannual);htrain=np.asarray(yhourly)[train]
    if np.any(a<=0) or np.any(htrain<=0):raise ValueError('Costs must be positive')
    logratio=np.log(htrain/a[train]);cv=[]
    for alpha in alphas:
        losses=[]
        for it,iv in LeaveOneGroupOut().split(x[train],groups=np.asarray(groups)[train]):
            model=make_pipeline(StandardScaler(),Ridge(alpha=alpha));model.fit(x[train][it],logratio[it]);losses.extend(np.abs(model.predict(x[train][iv])-logratio[iv]))
        cv.append(float(np.mean(losses)))
    best=int(np.argmin(cv));model=make_pipeline(StandardScaler(),Ridge(alpha=alphas[best]));model.fit(x[train],logratio)
    predictions={'annual':a[test].copy(),'uniform_adder':a[test]+float(np.mean(htrain-a[train])),'uniform_multiplier':a[test]*float(np.exp(np.mean(logratio))),'resource_ridge':a[test]*np.exp(model.predict(x[test]))}
    if any(np.any(~np.isfinite(v)) or np.any(v<=0) for v in predictions.values()):raise ValueError('Invalid predicted costs')
    return predictions,{'ridge_alpha':alphas[best],'inner_cv_mae_logratio':cv,'feature_standardization_mean':model[0].mean_.tolist(),'feature_standardization_scale':model[0].scale_.tolist(),'ridge_coefficients_standardized':model[1].coef_.tolist(),'ridge_intercept':float(model[1].intercept_)}

def verify_then_select(predicted,hourly,k):
    predicted=np.asarray(predicted);hourly=np.asarray(hourly)
    if k<0 or k>len(predicted):raise ValueError('Invalid verification count')
    order=np.argsort(predicted,kind='stable')
    queried=order[:k]
    # The oracle is consulted only after the query list is fixed.
    selected=int(queried[np.argmin(hourly[queried])]) if k else int(order[0])
    return selected,queried
