import argparse  # To parse command line arguments
import json  # To parse and dump JSON
import numpy as np
import pickle
from kafka import KafkaConsumer  # Import Kafka consumer
from kafka import KafkaProducer  # Import Kafka producer
from sklearn.ensemble import RandomForestRegressor


from Hawks_processes.Models.predict import HawksProcess

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("--broker-list", type=str, required=True, help="the broker list")
args = parser.parse_args()  # Parse arguments

consumer_properties = KafkaConsumer(
    "cascade_properties",  # Topic name
    bootstrap_servers=args.broker_list,  # List of brokers passed from the command line
    value_deserializer=lambda v: json.loads(
        v.decode("utf-8")
    ),  # How to deserialize the value from a binary buffer
    key_deserializer=lambda v: v.decode(),  # How to deserialize the key (if any)
)

consumer_learner = KafkaConsumer(
    "cascade_model",
    bootstrap_servers=args.broker_list,
    value_deserializer=lambda m: pickle.loads(m),
    key_deserializer=lambda v: v.decode(),  # How to deserialize the key (if any)
)


producer = KafkaProducer(
    bootstrap_servers=args.broker_list,  # List of brokers passed from the command line
    value_serializer=lambda v: json.dumps(v).encode(
        "utf-8"
    ),  # How to serialize the value to a binary buffer
    key_serializer=str.encode,  # How to serialize the key
)
# consumer.subscribe(["cascade_properties", "models"])
# check the two type of mesages either size or params use
# create dict with cid as a key to have all the data

cid_n_tot_dict = {}  # dictionnary with cid as keys and n_tot as values
cid_params_dict = {}  # dictionary with cid as keys and params as value

for msg in consumer_properties:
    alpha, mu = 2.4, 10
    msg_value = msg.value

    w_true = None

    if msg_value["type"] == "parameters":
        # { 'type': 'parameters', 'cid': 'tw23981', 'msg' : 'blah blah', 'n_obs': 32, 'n_supp' : 120, 'params': [ 0.0423, 124.312 ], n_star G1 }
        # Getting data from msg
        n_supp = msg_value["n_supp"]
        params = msg_value["params"]
        n_obs = msg_value["n_obs"]
        cid = msg_value["cid"]
        if cid not in cid_n_tot_dict.keys():
            cid_params_dict[cid] = msg_value
        else:
            n_tot = cid_n_tot_dict[cid]
            estimator = HawksProcess(
                alpha=alpha, mu=mu, n_star=n_star, params=params, G1=G1
            )
            n = estimator.prediction_one_shot(n_obs)
            try:
                w_true = (n_tot - n) * (1 - n_star) / G1
            except ZeroDivisionError:
                w_true = -1

        n_star = msg_value["n_star"]
        G1 = msg_value["G1"]

        T_obs = msg.key

    elif msg_value["type"] == "size":

        # { 'type' : 'size', 'cid': 'tw23981', 'n_tot': 127, 't_end': 4329 }
        cid = msg_value["cid"]
        n_tot = msg_value["n_tot"]

        t_end = msg_value["t_end"]
        T_obs = msg.key
        if cid not in cid_params_dict.keys():
            cid_n_tot_dict[cid] = n_tot

        else:

            msg_params = cid_params_dict[cid]
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
        print("N tot for T_obs is : " + str(T_obs) + " And cid is :" + str(cid))
        continue

    if w_true:
        key = T_obs
        value_sample = {
            "type": "sample",
            "cid": cid,
            "X": [params[1], G1, n_star],
            "W": w_true,
        }

    for msg_model in consumer_learner:
        break
    if msg_model:
        w_model = msg_model.value.predict([[params[1], G1, n_star]])
        n_model = n + w_model[0] * (G1 / (1 - n_star))
        T_obs = msg_model.key
        if n_model > 100:
            # Key = None Value = { 'type': 'alert', 'cid': 'tw23981', 'msg' : 'blah blah', 'T_obs': 600, 'n_tot' : 158 }
            alert_value = {
                "type": "alert",
                "cid": cid,
                "msg": "blah blah",
                "T_obs": key,
                "n_tot": n_model,
            }
            producer.send("cascade_alert", key=T_obs, value=alert_value)

        are = np.append(n_model - n_tot) / n_tot

        # Key = None Value = { 'type': 'stat', 'cid': 'tw23981', 'T_obs': 600, 'ARE' : 0.93 }
        stat_value = {
            "type": "stat",
            "cid": cid,
            "T_obs": key,
            "ARE": are,
        }

        producer.send("cascade_stat", key=T_obs, value=stat_value)

    producer.send("cascade_samples", key=T_obs, value=value_sample)

producer.flush()
