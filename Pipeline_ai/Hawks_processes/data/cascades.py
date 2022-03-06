import os
import pandas as pd


default_cascade_directory = "./cache/cascades"


def write_cascade(cascade, casc_index, cascade_directory=default_cascade_directory):
    """Save a cascade into a csv file

    Args:
        cascade (numpy array): (n,2) numpy array containing marked time points (t_i,m_i)
        casc_index (int): index of the cascade (int)
        cascade_directory (str, optional): directory where the file is saved. Defaults to default_cascade_directory.
    """

    if not os.path.exists(cascade_directory):
        os.makedirs(cascade_directory, exist_ok=False)
    df = pd.DataFrame(cascade, columns=["time", "magnitude"])
    df.to_csv(
        os.path.join(cascade_directory, "casc-{}.csv".format(casc_index)),
        columns=["time", "magnitude"],
    )


def read_cascade(casc_index, cascade_directory=default_cascade_directory):
    """Reads a cascade csv file and returns its cascade as a numpy array containing marked time points (t_i,m_i)

    Args:
        casc_index (int): index of the cascade (int)
        cascade_directory (str, optional): _description_. directory where the file is saved

    Returns:
        numpy array: numpy array containing marked time points
    """

    df = pd.read_csv(
        os.path.join(cascade_directory, "casc-{}.csv".format(casc_index)),
        names=["time", "magnitude"],
        header=0,
    )
    return df.to_numpy()
