import numpy as np
import scipy.optimize as optim

from Hawks_processes.Models.predict import HawksProcess
from Hawks_processes.utils import loglikelihood


class MAP(HawksProcess):
    """[summary]

    Args:
        HawksProcess ([type]): [description]
    """

    def __init__(
        self,
        alpha=None,
        mu=None,
        submodel_params=None,
        n_star=None,
        G1=None,
    ):
        super(MAP, self).__init__(
            alpha=alpha,
            mu=mu,
            submodel_params=submodel_params,
            n_star=G1,
            G1=G1,
        )

    def train(
        self,
        history,
        t,
        display=False,
        max_n_star=1,
    ):
        """Compute the loglikelyhood and the estimated parameters from a cascade history

        Args:
            history (numpy array): [(n,2) numpy array containing marked time points (t_i,m_i)]
            t (int): [current time (i.e end of observation window)]
            display (bool, optional): [display calculation]. Defaults to False.
            max_n_star (int, optional): [max value of n star]. Defaults to 1.

        Returns:
            [tuple]: [tuple of the value of the loglikelyhood and the parameters estimated]
        """

        # Compute prior moments
        mu_p, mu_beta, sig_p, sig_beta, corr = self.submodel_params["prior_params"]
        sample_mean = np.array([mu_p, mu_beta])
        cov_p_beta = corr * sig_p * sig_beta
        Q = np.array([[sig_p**2, cov_p_beta], [cov_p_beta, sig_beta**2]])

        # Apply method of moments
        cov_prior = np.log(
            Q / sample_mean.reshape((-1, 1)) / sample_mean.reshape((1, -1)) + 1
        )
        mean_prior = np.log(sample_mean) - np.diag(cov_prior) / 2.0

        # Compute the covariance inverse (precision matrix) once for all
        inv_cov_prior = np.asmatrix(cov_prior).I

        # Define the target function to minimize as minus the log of the a posteriori density
        def target(params):
            log_params = np.log(params)

            if np.any(np.isnan(log_params)):
                return np.inf
            else:
                dparams = np.asmatrix(log_params - mean_prior)
                prior_term = float(-1 / 2 * dparams * inv_cov_prior * dparams.T)
                logLL = loglikelihood(params, history, t)
                return -(prior_term + logLL)

        EM = self.mu * (self.alpha - 1) / (self.alpha - 2)
        eps = 1.0e-8

        # Set realistic bounds on p and beta
        p_min, p_max = eps, max_n_star / EM - eps
        beta_min, beta_max = 1 / (3600.0 * 24 * 10), 1 / (60.0 * 1)

        # Define the bounds on p (first column) and beta (second column)
        bounds = optim.Bounds(np.array([p_min, beta_min]), np.array([p_max, beta_max]))

        # Run the optimization
        res = optim.minimize(
            target,
            sample_mean,
            method="Powell",
            bounds=bounds,
            options={"xtol": 1e-8, "disp": display},
        )
        # Returns the loglikelihood and found parameters
        self.params = res.x

        return (-res.fun, res.x)


class MLE(HawksProcess):
    def __init__(
        self,
        alpha=None,
        mu=None,
        submodel_params=None,
        n_star=None,
        G1=None,
    ):
        """_summary_

        Args:
            alpha (_type_, optional): _description_. Defaults to None.
            mu (_type_, optional): _description_. Defaults to None.
            submodel_params (_type_, optional): _description_. Defaults to None.
            n_star (_type_, optional): _description_. Defaults to None.
            G1 (_type_, optional): _description_. Defaults to None.

        """
        super(MLE, self).__init__(
            alpha=alpha,
            mu=mu,
            submodel_params=submodel_params,
            n_star=n_star,
            G1=G1,
        )

        # super(HawksProcess, self).__init__(alpha=alpha, mu=mu)

    def train(
        self,
        history,
        t,
        display=False,
        max_n_star=1,
    ):
        """[summary]

        Args:
            history ([numpy array]): (n,2) numpy array containing marked time points (t_i,m_i)
            t ([int]): current time (i.e end of observation window)
            display (bool, optional): display calculation. Defaults to False.
            max_n_star (int, optional): max value of n star. Defaults to 1.

        Returns:
            tuple: tuple of the value of the loglikelyhood and the parameters estimated
        """

        # Define the target function to minimize as minus the loglikelihood
        target = lambda params: -loglikelihood(params, history, t)

        EM = self.mu * (self.alpha - 1) / (self.alpha - 2)
        eps = 1.0e-8

        # Set realistic bounds on p and beta
        p_min, p_max = eps, max_n_star / EM - eps
        beta_min, beta_max = 1 / (3600.0 * 24 * 10), 1 / (60.0 * 1)

        # Define the bounds on p (first column) and beta (second column)

        bounds = optim.Bounds(np.array([p_min, beta_min]), np.array([p_max, beta_max]))

        # Run the optimization

        res = optim.minimize(
            target,
            self.submodel_params["init_params"],
            method="Powell",
            bounds=bounds,
            options={"xtol": 1e-8, "disp": display},
        )
        self.params = res.x

        # Returns the loglikelihood and found parameters
        return (-res.fun, tuple(res.x))
