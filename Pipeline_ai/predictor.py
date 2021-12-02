import argparse  # To parse command line arguments
import json  # To parse and dump JSON
import numpy as np
import pickle
import sklearn
from kafka import KafkaConsumer  # Import Kafka consumer
from kafka import KafkaProducer  # Import Kafka producer
from sklearn.ensemble import RandomForestRegressor
import logger


from Hawks_processes.Models.predict import HawksProcess

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("--broker-list", type=str, required=True, help="the broker list")
args = parser.parse_args()  # Parse arguments


def deserializer(
    v,
):  # the deserializer depends on the topic. If it's not json, it's pickle
    try:
        return json.loads(v.decode("utf-8"))
    except UnicodeDecodeError:
        return pickle.loads(v)


consumer_properties = KafkaConsumer(
    "cascade_properties",  # Topic name
    bootstrap_servers=args.broker_list,  # List of brokers passed from the command line
    value_deserializer=lambda v: json.loads(
        v.decode("utf-8")
    ),  # How to deserialize the value from a binary buffer
    key_deserializer=lambda v: v.decode(),  # How to deserialize the key (if any)
)

consumer = KafkaConsumer(
    bootstrap_servers=args.broker_list,
    value_deserializer=lambda m: deserializer(m),
    key_deserializer=lambda v: v.decode(),  # How to deserialize the key (if any)
    request_timeout_ms=1000,
)


producer = KafkaProducer(
    bootstrap_servers=args.broker_list,  # List of brokers passed from the command line
    value_serializer=lambda v: json.dumps(v).encode(
        "utf-8"
    ),  # How to serialize the value to a binary buffer
    key_serializer=str.encode,  # How to serialize the key
)

logger = logger.get_logger("predictor", broker_list=args.broker_list, debug=True)
consumer.subscribe(["cascade_properties", "cascade_model"])

cid_n_tot_dict = {}  # dictionnary with cid as keys and n_tot as values
cid_params_dict = {}  # dictionary with cid as keys and params as value
dict_model = {"300": None, "600": None, "1200": None}
model = None
n_tot = None
n_star = None


for msg in consumer:
    alpha, mu = 2.4, 10
    msg_value = msg.value
    w_true = None

    if msg.topic == "cascade_model":
        logger.debug("Received a model!")
        logger.debug("model for observation " + msg.key)
        model = msg.value
        dict_model[msg.key] = model

    else:
        if msg_value["type"] == "parameters":

            # { 'type': 'parameters', 'cid': 'tw23981', 'msg' : 'blah blah', 'n_obs': 32, 'n_supp' : 120, 'params': [ 0.0423, 124.312 ], n_star G1 }
            # Getting data from msg
            n_supp = msg_value["n_supp"]
            params = msg_value["params"]
            n_obs = msg_value["n_obs"]
            cid = msg_value["cid"]
            n_star = msg_value["n_star"]
            G1 = msg_value["G1"]
            key = msg.key

            if (cid, key) not in cid_n_tot_dict.keys():
                cid_params_dict[(cid, key)] = msg_value
            else:
                n_tot = cid_n_tot_dict[(cid, key)]
                estimator = HawksProcess(
                    alpha=alpha, mu=mu, n_star=n_star, params=params, G1=G1
                )
                n = estimator.prediction_one_shot(n_obs)
                try:
                    w_true = (n_tot - n) * (1 - n_star) / G1
                except ZeroDivisionError:
                    w_true = -1

            T_obs = msg.key

        elif msg_value["type"] == "size":

            # { 'type' : 'size', 'cid': 'tw23981', 'n_tot': 127, 't_end': 4329 }
            cid = msg_value["cid"]
            n_tot = msg_value["n_tot"]

            t_end = msg_value["t_end"]
            T_obs = msg.key
            if (cid, T_obs) not in cid_params_dict.keys():
                cid_n_tot_dict[(cid, T_obs)] = n_tot

            else:

                msg_params = cid_params_dict[(cid, key)]
                n_star = msg_params["n_star"]
                G1 = msg_params["G1"]
                params = msg_params["params"]
                estimator = HawksProcess(
                    alpha=alpha, mu=mu, n_star=n_star, params=params, G1=G1
                )
                n = estimator.prediction_one_shot(n_obs)
                try:
                    w_true = (n_tot - n) * (1 - n_star) / G1
                except ZeroDivisionError:
                    w_true = -1
        else:
            continue

    if w_true:
        key = T_obs
        value_sample = {
            "type": "sample",
            "cid": cid,
            "X": [params[1], G1, n_star],
            "W": w_true,
        }

        producer.send("cascade_samples", key=T_obs, value=value_sample)
    if n_star is not None:
        estimator = HawksProcess(
            alpha=alpha, mu=mu, n_star=n_star, params=params, G1=G1
        )
        n = estimator.prediction_one_shot(n_obs)
        if dict_model[msg.key]:
            model = dict_model[msg.key]

        # w_model = model.predict([[params[1], G1, n_star]])
        # n_model = n + w_model[0] * (G1 / (1 - n_star))
        n_model = estimator.prediction_one_shot(n, model)

        T_obs = msg.key
        if n_model > 150:
            # Key = None Value = { 'type': 'alert', 'cid': 'tw23981', 'msg' : 'blah blah', 'T_obs': 600, 'n_tot' : 158 }
            alert_value = {
                "type": "alert",
                "cid": cid,
                "msg": "blah blah",
                "T_obs": T_obs,
                "n_tot": int(n_model),
            }
            logger.info(
                "Viral Tweet n_tot "
                + str(n_model)
                + " observation window "
                + str(T_obs)
            )

            producer.send("cascade_alert", key=T_obs, value=alert_value)
        if n_tot:
            logger.info(
                "======================================="
                "stat" + "======================================="
            )
            are = np.abs(n_model - n_tot) / n_tot

            # Key = None Value = { 'type': 'stat', 'cid': 'tw23981', 'T_obs': 600, 'ARE' : 0.93 }
            stat_value = {
                "type": "stat",
                "cid": cid,
                "T_obs": key,
                "ARE": are,
            }
            logger.info(
                "=====================================New insight!========================="
            )
            logger.debug(
                "true   "
                + str(n_tot)
                + "   predicted  "
                + str(n_model)
                + "   Tobs "
                + str(T_obs)
            )
            logger.debug("ARE value " + str(are))
            logger.info("==============================================")

            producer.send("cascade_stat", key=T_obs, value=stat_value)
            n_tot = None


producer.flush()
