import argparse  # To parse command line arguments
import json  # To parse and dump JSON
import numpy as np
from kafka import KafkaConsumer  # Import Kafka consumer
from kafka import KafkaProducer  # Import Kafka producer
from sklearn.ensemble import RandomForestRegressor
from util import deserializer
from utils.predictor_utils import Predictor
import logger


from Hawks_processes.Models.predict import HawksProcess

alpha, mu = 2.4, 10
cid = None
samples = []
n_star = None
w_true_old = np.inf


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("--broker-list", type=str, required=True, help="the broker list")
args = parser.parse_args()  # Parse arguments


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

predictor = Predictor()


for msg in consumer:

    predictor.get_model(msg)

    values = predictor.get_values(
        msg,
        topic_model="cascade_model",
    )

    if values:
        w_true, cid, T_obs = values

    if cid:
        params, G1, n_star, n_obs, n_tot = predictor.get_params(cid, T_obs)

        if w_true and w_true != w_true_old:
            w_true_old = w_true

            value_sample = {
                "type": "sample",
                "cid": cid,
                "X": [params[1], G1, n_star],
                "W": w_true,
            }
            if value_sample not in samples:
                samples.append(value_sample)

            if len(samples) % 5 == 0:
                producer.send("cascade_samples", key=T_obs, value=value_sample)

    if n_star is not None:
        estimator = HawksProcess(
            alpha=alpha, mu=mu, n_star=n_star, params=params, G1=G1
        )
        n = estimator.prediction_one_shot(n_obs)
        model = predictor.dict_model[msg.key]

        n_model = estimator.prediction_one_shot(n, model)

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
                "T_obs": T_obs,
                "ARE": are,
            }
            logger.info(
                "=====================================New insight!========================="
            )

            logger.info("ARE value :" + str(are))
            logger.info("==============================================")

            producer.send("cascade_stat", key=T_obs, value=stat_value)

            predictor.cid_n_tot_dict.pop((cid, T_obs), None)


producer.flush()
