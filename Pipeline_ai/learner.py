# External Import
import argparse  # To parse command line arguments
import json  # To parse and dump JSON
from kafka import KafkaConsumer  # Import Kafka consumer
from kafka import KafkaProducer  # Import Kafka producder
from sklearn.ensemble import RandomForestRegressor
import pickle


# Topics's name


# topics'key
# key_dic ={"300":0, "600":1, "1200":2}


# Arguments to write to run the file in a terminal  "python3 Hawkes --broker-list localhost:9092 --obs-wind 300".
parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("--broker-list", type=str, required=True, help="the broker list")
parser.add_argument(
    "--obs-wind", type=str, required=True, help="the observation window : 300/600/1200"
)  # In order to // the calculs.
args = parser.parse_args()  # Parse arguments

producer_models = KafkaProducer(
    bootstrap_servers=args.broker_list,  # List of brokers passed from the command line
    value_serializer=lambda m: pickle.dumps(
        m
    ),  # How to serialize the value to a binary buffer using pickle this time because we send a forest not a message.
)

# Consumer
consumer_samples = KafkaConsumer(
    "cascade_samples",
    bootstrap_servers=args.broker_list,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    key_deserializer=lambda v: v.decode(),
    auto_offset_reset="earliest",
    group_id="SamplesConsumerGroup-{}".format(args.obs_wind),
)


features = []
targets = []


# Reading samples topic.
for msg in consumer_samples:

    # Getting the data from msg
    T_obs = msg.key
    msg = msg.value
    features.append(msg["X"])
    w = msg["W"]
    targets.append(w)

    if len(features) % 10 == 0:

        regr = RandomForestRegressor()  # We compute a new forest.
        model = regr.fit(features, targets)

        producer_models.send("cascade_model", model)
producer_models.flush()
