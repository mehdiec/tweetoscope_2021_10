from Hawks_processes.Models.predict import HawksProcess

alpha, mu = 2.4, 10


def calculate_w_true(n_obs, n_tot, n_star, G1, estimator):
    n = estimator.prediction_one_shot(n_obs)
    try:
        w_true = (n_tot - n) * (1 - n_star) / G1
    except ZeroDivisionError:
        w_true = -1
    return w_true


class Predictor:
    def __init__(
        self,
        dict_model=None,
        cid_params_dict=None,
        cid_n_tot_dict=None,
        w_true=None,
    ):

        if dict_model is None:
            dict_model = {"300": None, "600": None, "1200": None}

        if cid_params_dict is None:
            cid_params_dict = {}

        if cid_n_tot_dict is None:
            cid_n_tot_dict = {}

        self.cid_n_tot_dict = cid_n_tot_dict
        self.cid_params_dict = cid_params_dict
        self.dict_model = dict_model
        self.w_true = w_true

    def get_model(self, msg):

        T_obs = msg.key
        if msg.topic == "cascade_model":

            model = msg.value
            self.dict_model[T_obs] = model

    def get_values(
        self,
        msg,
        topic_model="cascade_model",
    ):
        self.w_true = None
        msg_value = msg.value
        T_obs = msg.key
        cid = None
        if msg.topic != topic_model:
            if msg_value["type"] == "parameters":

                # { 'type': 'parameters', 'cid': 'tw23981', 'msg' : 'blah blah', 'n_obs': 32, 'n_supp' : 120, 'params': [ 0.0423, 124.312 ], n_star G1 }
                # Getting data from msg
                params = msg_value["params"]
                n_obs = msg_value["n_obs"]
                cid = msg_value["cid"]
                n_star = msg_value["n_star"]
                G1 = msg_value["G1"]
                self.cid_params_dict[(cid, T_obs)] = msg_value

                if (cid, T_obs) in self.cid_n_tot_dict.keys():

                    n_tot = self.cid_n_tot_dict[(cid, T_obs)]
                    estimator = HawksProcess(
                        alpha=alpha, mu=mu, n_star=n_star, params=params, G1=G1
                    )
                    self.w_true = calculate_w_true(n_obs, n_tot, n_star, G1, estimator)

            elif msg_value["type"] == "size":

                # { 'type' : 'size', 'cid': 'tw23981', 'n_tot': 127, 't_end': 4329 }
                cid = msg_value["cid"]
                n_tot = msg_value["n_tot"]
                self.cid_n_tot_dict[(cid, T_obs)] = n_tot
                if (cid, T_obs) in self.cid_params_dict.keys():

                    msg_params = self.cid_params_dict[(cid, T_obs)]
                    n_star = msg_params["n_star"]
                    G1 = msg_params["G1"]
                    params = msg_params["params"]
                    n_obs = msg_params["n_obs"]
                    estimator = HawksProcess(
                        alpha=alpha, mu=mu, n_star=n_star, params=params, G1=G1
                    )
                    self.w_true = calculate_w_true(n_obs, n_tot, n_star, G1, estimator)
            if cid:
                return [self.w_true, cid, T_obs]
            else:
                return []

    def get_params(self, cid, T_obs):
        params, G1, n_star, n_obs, n_tot = None, None, None, None, None

        if (cid, T_obs) in self.cid_params_dict.keys():
            msg_params = self.cid_params_dict[(cid, T_obs)]
            n_star = msg_params["n_star"]
            G1 = msg_params["G1"]
            params = msg_params["params"]
            n_obs = msg_params["n_obs"]
        if (cid, T_obs) in self.cid_n_tot_dict.keys():
            n_tot = self.cid_n_tot_dict[(cid, T_obs)]

        return params, G1, n_star, n_obs, n_tot
