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
        n_star=None,
        G1=None,
        params=None,
        submodel_params=None,
        estimator=None,
    ):
        """_summary_

        Args:
            alpha (float): power parameter of the power-law mark distribution
            mu (float): min value parameter of the power-law mark distribution
            n_star (_type_, optional): _description_. Defaults to None.
            G1 (_type_, optional): _description_. Defaults to None.
            params (tuple, optional): parameter tuple (p,beta) of the Hawkes process. Defaults to None.
            submodel_params (dict, optional): different parameters for models. Defaults to None.
            estimator (str, optional): name of the estimator. Defaults to None.
        """
        if submodel_params is None:
            submodel_params = {
                "init_params": np.array([0.0001, 1.0 / 60]),
                "prior_params": [0.02, 0.0002, 0.01, 0.001, -0.1],
            }

        if params is None:
            params = (0.01, 1 / 3600.0)
        self.params = params

        self.submodel_params = dict(submodel_params)

        self.n_star = n_star
        self.G1 = G1
        self.alpha = alpha
        self.mu = mu
        if not estimator:
            estimator = None
        self.estimator = get_model_class(estimator)
        self.to_send = np.array([])

    def train(
        self,
        history,
        t,
        display=False,
        max_n_star=1,
    ):
        raise NotImplementedError

    def prediction(self, history, t, model=None):
        """Returns the expected total numbers of points for a set of time points

        Args:
            history (array): (n,2) numpy array containing marked time points (t_i,m_i)
            t (int): current time (i.e end of observation window)
            model (_type_, optional): random forest model. Defaults to None.

        Raises:
            Exception: unusal value for n_star

        Returns:
            int: total numbers of points
        """

        p, beta = self.params

        tis = history[:, 0]
        EM = self.mu * (self.alpha - 1) / (self.alpha - 2)

        self.n_star = p * EM

        if self.n_star >= 2:
            raise Exception(f"Branching factor {self.n_star:.2f} greater than one")

        n = len(history)
        I = history[:, 0] < t
        tis = history[I, 0]
        mis = history[I, 1]
        self.G1 = p * np.sum(mis * np.exp(-beta * (t - tis)))

        Ntot = n + self.G1 / (1.0 - self.n_star)

        return Ntot

    def prediction_one_shot(self, n, model=None):
        """Returns the expected total numbers of points for a set of time points

        Args:
            n (int): observation size
            model (_type_, optional): random forest model. Defaults to None.

        Raises:
             Exception: unusal value for n_star

        Returns:
            int: total numbers of points
        """

        p, beta = self.params

        if self.n_star >= 2:
            raise Exception(f"Branching factor {self.n_star:.2f} greater than one")

        if model is not None:
            omega = model.predict(
                np.array([beta, self.G1, self.n_star]).reshape(1, -1)
            )[0]

            Ntot = n + omega * self.G1 / (1.0 - self.n_star)

        else:

            Ntot = n + self.G1 / (1.0 - self.n_star)

        return Ntot
