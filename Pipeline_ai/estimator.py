import argparse
import json
import numpy as np

from kafka import KafkaConsumer  # Import Kafka consumer
from kafka import KafkaProducer  # Import Kafka producer

import logger
from Hawks_processes.Models.estimation import MAP

alpha, mu = 2.4, 10

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("--broker-list", type=str, required=True, help="the broker list")
args = parser.parse_args()  # Parse arguments

consumer = KafkaConsumer(
    "cascade_series",  # Topic name
    # Topic name
    bootstrap_servers=args.broker_list,  # List of brokers passed from the command line
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)

producer = KafkaProducer(
    bootstrap_servers=args.broker_list,  # List of brokers passed from the command line
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    key_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

logger = logger.get_logger("estimator", broker_list=args.broker_list, debug=True)

for msg in consumer:

    # We chose the MAP estimator
    estimator = MAP(alpha, mu)

    msg = msg.value

    # Getting data from msg
    T_obs = msg["T_obs"]
    hist = msg["tweets"]
    history = np.array(hist)
    n_obs = len(history)
    cid = msg["cid"]
    message = msg["msg"]

    estimator.train(history, T_obs)
    params = estimator.params
    N_tot = estimator.prediction(history, T_obs, params)

    key = T_obs

    value = {
        "type": "parameters",
        "cid": cid,
        "msg": 0,
        "n_obs": n_obs,
        "n_supp": N_tot,
        "params": tuple(params),
        "n_star": estimator.n_star,
        "G1": estimator.G1,
    }

    logger.info("sending properties ")
    producer.send("cascade_properties", key=key, value=value)
producer.flush()
