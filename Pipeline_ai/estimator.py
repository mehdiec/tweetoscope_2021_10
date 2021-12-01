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
    # Topic name
    bootstrap_servers=args.broker_list,  # List of brokers passed from the command line
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)

producer = KafkaProducer(
    bootstrap_servers=args.broker_list,  # List of brokers passed from the command line
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    key_serializer=lambda v: json.dumps(v).encode("utf-8"),
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
    producer.send("cascade_properties", key=key, value=value)
producer.flush()
