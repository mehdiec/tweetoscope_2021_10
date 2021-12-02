import argparse
import json
import pickle

from kafka import KafkaConsumer  # Import Kafka consumer
from kafka import KafkaProducer  # Import Kafka producder
from sklearn.ensemble import RandomForestRegressor

import logger

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
logger = logger.get_logger("learner", broker_list=args.broker_list, debug=True)


dict_obs_features_target = {
    "300": {"features": [], "targets": []},
    "600": {"features": [], "targets": []},
    "1200": {"features": [], "targets": []},
}


for msg in consumer_samples:

    T_obs = msg.key
    features = dict_obs_features_target[T_obs]["features"]
    targets = dict_obs_features_target[T_obs]["targets"]

    msg = msg.value
    features.append(msg["X"])
    w = msg["W"]
    targets.append(w)

    logger.debug("learner do be learning number of samples:" + str(len(features)))
    regr = RandomForestRegressor()  # We compute a new forest.
    model = regr.fit(features, targets)
    logger.info("New model for T_obs =" + str(T_obs))

    producer_models.send("cascade_model", key=T_obs, value=model)

producer_models.flush()
