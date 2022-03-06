import numpy as np


from Hawks_processes.utils import multivariate_log_normal
from Hawks_processes.data.cascades import write_cascade


def neg_power_law(alpha, mu, size=1):
    """Returns a 1D-array of samples drawn from a negative power law distribution

    Args:
        alpha (float): power parameter of the power-law mark distribution
        mu (float): min value parameter of the power-law mark distribution
        size (int, optional): number of samples. Defaults to 1.

    Returns:
        array: 1D-array of samples
    """

    u = np.random.uniform(size=size)
    X = mu * np.exp(np.log(u) / (1.0 - alpha))
    if size == 1:
        return X[0]
    else:
        return X


class SimulateProcess:
    """Class that generate cascade"""

    def __init__(
        self,
        params,
        m0,
        alpha,
        mu,
    ):
        """

        Args:
            params (tuple): parameter tuple (p,beta) of the generating process
            m0 (float): magnitude of the initial tweet at t = 0.
            alpha (float): power parameter of the power-law mark distribution
            mu (flaot): min value parameter of the power-law mark distribution
        """
        self.params = params
        self.m0 = m0  # number of folower
        self.alpha = alpha
        self.mu = mu

    def simulate_marked_exp_hawkes_process(self, max_size=10000):
        """Returns a 2D-array whose rows contain marked time points simulated from an exponential Hawkes process

        Args:
            max_size (int, optional): maximal authorized size of the cascade. Defaults to 10000.

        Returns:
            array: 2D-array whose rows contain marked time points
        """

        p, beta = self.params
        # The result is just a 1D array
        # However for further compatibility, we reserve a second colum for the magnitude of every point.
        # Every row thus describes a marked timepoint (ti, mi) with a magnitude set arbitrarily to one.

        # Create an unitialized array for optimization purpose (only memory allocation)
        T = np.empty((max_size, 2), dtype=float)

        # Set magnitudes to m0.

        intensity = p * beta * self.m0
        t, m = 0.0, self.m0

        # Main loop

        for i in range(max_size):
            # Save the current point before generating the next one.
            T[i] = t, m

            # Sample inter-event time v from a homogeneous Poisson process
            u = np.random.uniform()
            v = -np.log(u)

            # Apply the inversion equation
            w = 1.0 - beta / intensity * v
            # Tests if process stops generating points.
            if w <= 0.0:
                # Shrink T to remove unused rows
                T = T[:i, :]
                break
            # Otherwise computes the time jump dt and new time point t
            dt = -np.log(w) / beta
            t += dt
            m = neg_power_law(self.alpha, self.mu)

            lambda_1 = m * p
            # And update intensity accordingly
            intensity = intensity * np.exp(-beta * dt) + beta * lambda_1
        return T

    def generate_pseudo_data(self, n, prior_params):
        """Sample cascades from some parameter prior and save them on disk.

        Args:
            n (int): number of cascades to generate
            prior_params (list): list (mu_p, mu_beta, sig_p, sig_beta, corr) of hyper parameters of the prior
        """

        # Generate parameters from prior
        mu_p, mu_beta, sig_p, sig_beta, corr = prior_params
        mu_params = [mu_p, mu_beta]
        cov_p_beta = corr * sig_p * sig_beta
        Q = np.array([[sig_p**2, cov_p_beta], [cov_p_beta, sig_beta**2]])
        params = multivariate_log_normal(mu_params, Q, size=n)
        # Then generate cascades
        for i, (p, beta) in enumerate(params):
            self.params = p, beta
            cascade = self.simulate_marked_exp_hawkes_process()
            write_cascade(cascade, i)
