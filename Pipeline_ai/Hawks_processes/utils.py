import os
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy import stats


def loglikelihood(params, history, t):
    """
    Returns the loglikelihood of a Hawkes process with exponential kernel
    computed with a linear time complexity

    params   -- parameter tuple (p,beta) of the Hawkes process
    history  -- (n,2) numpy array containing marked time points (t_i,m_i)
    t        -- current time (i.e end of observation window)
    """

    p, beta = params

    if p <= 0 or p >= 1 or beta <= 0.0:
        return -np.inf

    n = len(history)
    tis = history[:, 0]
    mis = history[:, 1]

    LL = (n - 1) * np.log(p * beta)
    logA = -np.inf
    prev_ti, prev_mi = history[0]

    i = 0
    for ti, mi in history[1:]:
        if prev_mi + np.exp(logA) <= 0:
            print("Bad value", prev_mi + np.exp(logA))

        logA = np.log(prev_mi + np.exp(logA)) - beta * (ti - prev_ti)
        LL += logA
        prev_ti, prev_mi = ti, mi
        i += 1

    logA = np.log(prev_mi + np.exp(logA)) - beta * (t - prev_ti)
    LL -= p * (np.sum(mis) - np.exp(logA))

    return LL


def multivariate_log_normal(mu, cov, size=1):
    """
    Returns a (size,2)-array containing iid samples of (p,beta) drawn from a given prior distribution

    mu   -- mean vector of size 2
    cov  -- covariance matrix of size 2
    size -- number of samples
    """

    mu, cov = np.asarray(mu), np.asarray(cov)
    cov_on_log = np.log(cov / mu.reshape((-1, 1)) / mu.reshape((1, -1)) + 1)
    mean_on_log = np.log(mu) - np.diag(cov_on_log) / 2.0

    log_params = np.random.multivariate_normal(mean_on_log, cov_on_log, size=size)
    return np.exp(log_params)
