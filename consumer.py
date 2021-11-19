import argparse                   # To parse command line arguments
import json                       # To parse and dump JSON
from kafka import KafkaConsumer   # Import Kafka consumer
from kafka import KafkaProducer   # Import Kafka producer

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('--broker-list', type=str, required=True, help="the broker list")
args = parser.parse_args()  # Parse arguments

consumer = KafkaConsumer('tweets',                   # Topic name
  bootstrap_servers = args.broker_list,                        # List of brokers passed from the command line
  value_deserializer=lambda v: json.loads(v.decode('utf-8')),  # How to deserialize the value from a binary buffer
  key_deserializer= lambda v: v.decode()                       # How to deserialize the key (if any)
)

producer = KafkaProducer(
  bootstrap_servers = args.broker_list,                     # List of brokers passed from the command line
  value_serializer=lambda v: json.dumps(v).encode('utf-8'), # How to serialize the value to a binary buffer
  key_serializer=str.encode                                 # How to serialize the key
)


serie={}
T_fin_cascade=3600 #1h
T1_fenetre=600 #10mins

for msg in consumer:                            # Blocking call waiting for a new message
    #print (f"msg: ({msg.key}, {msg.value})")    # Write key and payload of the received message
    x = msg.key
    y = msg.value
    if y["tweet_id"] not in serie:
        serie[y["tweet_id"]] = {'type' : "serie", 'cid' : y["tweet_id"], 'msg' : y["msg"], 'T_obs' : 0, 'tweets': [(y["t"],y["m"])]}
    else:
        serie[y["tweet_id"]]["tweets"].append((y["t"],y["m"]))
        tf= serie[y["tweet_id"]]["tweets"][-1][0]
        td= serie[y["tweet_id"]]["tweets"][-2][0]
        delta_t = tf-td

        t_start= serie[y["tweet_id"]]["tweets"][0][0]
        t_obs = tf-t_start

        if(delta_t >= T_fin_cascade or t_obs >= T1_fenetre) :
            serie[y["tweet_id"]]["T_obs"] = t_obs
            producer.send("cascade_series", key='None', value=serie[y["tweet_id"]])
            producer.flush()

