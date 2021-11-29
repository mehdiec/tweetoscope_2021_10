import numpy as np


def get_model_class(model_class):
    from Hawks_processes.Models.estimation import MAP, MLE

    if model_class == "MAP":
        return MAP
    if model_class == "MLE":
        return MLE
    else:
        return None


class HawksProcess:
    def __init__(
        self,
        alpha,
        mu,
        submodel_params=None,
        estimator=None,
    ):
        if submodel_params is None:
            submodel_params = {
                "params": (0.01, 1 / 3600.0),
                "init_params": np.array([0.0001, 1.0 / 60]),
                "prior_params": [0.02, 0.0002, 0.01, 0.001, -0.1],
            }
        self.submodel_params = dict(submodel_params)

        self.alpha = alpha
        self.mu = mu
        if not estimator:
            estimator = None
        self.estimator = get_model_class(estimator)

    def train(
        self,
        history,
        t,
        display=False,
        max_n_star=1,
    ):
        raise NotImplementedError

    def prediction(self, history, t, params):
        """
        Returns the expected total numbers of points for a set of time points

        params   -- parameter tuple (p,beta) of the Hawkes process
        history  -- (n,2) numpy array containing marked time points (t_i,m_i)
        alpha    -- power parameter of the power-law mark distribution
        mu       -- min value parameter of the power-law mark distribution
        t        -- current time (i.e end of observation window)
        """

        p, beta = params

        tis = history[:, 0]
        EM = self.mu * (self.alpha - 1) / (self.alpha - 2)

        n_star = p * EM

        if n_star >= 2:
            raise Exception(f"Branching factor {n_star:.2f} greater than one")

        n = len(history)
        I = history[:, 0] < t
        tis = history[I, 0]
        mis = history[I, 1]
        G1 = p * np.sum(mis * np.exp(-beta * (t - tis)))

        Ntot = n + G1 / (1.0 - n_star)

        return Ntot

    def predict(self, history, T=None):
        """
        Returns the expected total numbers of points for a set of time points

        params   -- parameter tuple (p,beta) of the Hawkes process
        history  -- (n,2) numpy array containing marked time points (t_i,m_i)
        alpha    -- power parameter of the power-law mark distribution
        mu       -- min value parameter of the power-law mark distribution
        T        -- 1D-array of times (i.e ends of observation window)
        """

        p, beta = self.submodel_params["params"]

        tis = history[:, 0]
        if T is None:
            T = np.linspace(60, tis[-1], 1000)

        N = np.zeros((len(T), 2))
        N[:, 0] = T

        EM = self.mu * (self.alpha - 1) / (self.alpha - 2)
        n_star = p * EM

        if n_star >= 1:

            raise Exception(f"Branching factor {n_star:.2f} greater than one")

        Si, ti_prev, i = 0.0, 0.0, 0

        for j, t in enumerate(T):
            for (ti, mi) in history[i:]:
                if ti >= t:
                    break

                Si = Si * np.exp(-beta * (ti - ti_prev)) + mi
                ti_prev = ti
                i += 1

            n = i + 1
            G1 = p * Si * np.exp(-beta * (t - ti_prev))
            N[j, 1] = n + G1 / (1.0 - n_star)

        return N

    def fit_predict(self, history, T=None, n_tries=10):

        """
        Compute the provided estimator for different observation windows and apply prediction according to it. Returns
        * the expected total numbers of points for a set of time points as a 1D-array
        * the computed loglikelihoods as a 1D-array
        * the estimated parameters as a 2D-array

        estimator -- function that implements an estimator that expect the same arguments as compute_MLE
        history   -- (n,2) numpy array containing marked time points (t_i,m_i)
        alpha     -- power parameter of the power-law mark distribution
        mu        -- min value parameter of the power-law mark distribution
        T         -- 1D-array of times (i.e ends of observation window)
        n_tries   -- number of times the estimator is run. Best result is kept.
        """

        tis = history[:, 0]
        if T is None:
            T = np.linspace(
                60, tis[-1], 50
            )  # Compute 50 points from 1min to last time point

        N = np.zeros((len(T), 2))
        N[:, 0] = T
        LLs = np.zeros((len(T), 2))
        LLs[:, 0] = T
        params = np.zeros((len(T), 3))
        params[:, 0] = T

        for i, t in enumerate(T):

            partial_history = history[tis < t]
            best_LL, self.submodel_params["params"], best_N_tot = -np.inf, None, np.inf

            estim = self.estimator(
                alpha=self.alpha,
                mu=self.mu,
                submodel_params=self.submodel_params["params"],
            )
            for _ in range(n_tries):

                if self.estimator is None:
                    return None

                LL, param = estim.train(partial_history, t, max_n_star=2)

                if LL > best_LL:
                    N_tot = self.prediction(partial_history, t, param)
                    estim.submodel_params["params"] = param

                    self.submodel_params["params"] = param

                    best_LL, best_N_tot = (
                        LL,
                        N_tot,
                    )

            N[i, 1], LLs[i, 1], params[i, 1:] = (
                best_N_tot,
                best_LL,
                estim.submodel_params["params"],
            )
        return N, LLs, params
