import argparse  # To parse command line arguments
import json  # To parse and dump JSON
import numpy as np
from kafka import KafkaConsumer  # Import Kafka consumer
from kafka import KafkaProducer  # Import Kafka producer

from Hawks_processes.Models.estimation import MAP

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("--broker-list", type=str, required=True, help="the broker list")
args = parser.parse_args()  # Parse arguments

consumer = KafkaConsumer(
    "cascade_series",  # Topic name
    bootstrap_servers=args.broker_list,  # List of brokers passed from the command line
    value_deserializer=lambda v: json.loads(
        v.decode("utf-8")
    ),  # How to deserialize the value from a binary buffer
    key_deserializer=lambda v: v.decode(),  # How to deserialize the key (if any)
)

producer = KafkaProducer(
    bootstrap_servers=args.broker_list,  # List of brokers passed from the command line
    value_serializer=lambda v: json.dumps(v).encode(
        "utf-8"
    ),  # How to serialize the value to a binary buffer
    key_serializer=str.encode,  # How to serialize the key
)


for msg in consumer:
    alpha, mu = 2.4, 10
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
    params = (estimator.alpha, estimator.beta)
    N_tot = estimator.prediction(history, T_obs, params)

    key = T_obs

    value = {
        "type": "parameters",
        "cid": cid,
        "msg": msg,
        "n_obs": n_obs,
        "n_supp": N_tot,
        "params": params,
        "n_star": estimator.n_star,
        "G1": estimator.G1,
    }
    producer.send("cascade_series", key=key, value=value)
producer.flush()
