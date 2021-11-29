import argparse  # To parse command line arguments
import json  # To parse and dump JSON
import numpy as np
import pickle
from kafka import KafkaConsumer  # Import Kafka consumer
from kafka import KafkaProducer  # Import Kafka producer

from Hawks_processes.Models.predict import HawksProcess

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("--broker-list", type=str, required=True, help="the broker list")
args = parser.parse_args()  # Parse arguments

consumer_series = KafkaConsumer(
    "cascade_series",  # Topic name
    bootstrap_servers=args.broker_list,  # List of brokers passed from the command line
    value_deserializer=lambda v: json.loads(
        v.decode("utf-8")
    ),  # How to deserialize the value from a binary buffer
    key_deserializer=lambda v: v.decode(),  # How to deserialize the key (if any)
)

consumer_samples = KafkaConsumer(
    "cascade_samples",
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
for msg in consumer_series:
    alpha, mu = 2.4, 10

    # Getting data from msg
    n_supp = msg["n_supp"]
    params = msg["params"]
    n_obs = msg["n_obs"]
    cid = msg["cid"]
    message = msg["msg"]
    n_star = msg["n_star"]
    G1 = msg["G1"]
    n_tot = msg["n_tot"]
    T_obs = msg["T_obs"]
    estimator = HawksProcess(alpha=alpha, mu=mu, n_star=n_star, params=params, G1=G1)

    producer.send("cascade_samples", key=T_obs, value=value_sample)

producer.flush()
