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


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("--broker-list", type=str, required=True, help="the broker list")

args = parser.parse_args()  # Parse arguments

producer_models = KafkaProducer(
    bootstrap_servers=args.broker_list,  # List of brokers passed from the command line
    value_serializer=lambda m: pickle.dumps(
        m
    ),  # How to serialize the value to a binary buffer using pickle this time because we send a forest not a message.
    key_serializer=str.encode,
)

# Consumer
consumer_samples = KafkaConsumer(
    "cascade_samples",
    bootstrap_servers=args.broker_list,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    key_deserializer=lambda v: v.decode(),
    auto_offset_reset="earliest",
)


features = []
targets = []
time2train = [i for i in range(1, 21)]

# Reading samples topic.
for msg in consumer_samples:

    # Getting the data from msg
    T_obs = msg.key
    msg = msg.value
    features.append(msg["X"])
    w = msg["W"]
    targets.append(w)

    if (len(features) % 10 == 0) or len(features) in time2train:

        print("learner do be learning", len(features))

        regr = RandomForestRegressor()  # We compute a new forest.
        model = regr.fit(features, targets)

        producer_models.send("cascade_model", key=T_obs, value=model)
producer_models.flush()
