import pickle
import sklearn


def deserializer(
    v,
):  # the deserializer depends on the topic. If it's not json, it's pickle
    try:
        return json.loads(v.decode("utf-8"))
    except UnicodeDecodeError:
        return pickle.loads(v)
