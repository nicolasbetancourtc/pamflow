""" Utilities to compute graphical soundscapes from audio files 

The functions here are a variant of the original graphical soundscapes introduced by Campos-Cerqueira et al. The peaks are detected on the spectrogram instead of detecting peaks on the spectrum. Results are similar but not equal to the ones computed using seewave in R.

References:
  - Campos‐Cerqueira, M., et al., 2020. How does FSC forest certification affect the acoustically active fauna in Madre de Dios, Peru? Remote Sensing in Ecology and Conservation 6, 274–285. https://doi.org/10.1002/rse2.120
  - Furumo, P.R., Aide, T.M., 2019. Using soundscapes to assess biodiversity in Neotropical oil palm landscapes. Landscape Ecology 34, 911–923.
  - Campos-Cerqueira, M., Aide, T.M., 2017. Changes in the acoustic structure and composition along a tropical elevational gradient. JEA 1, 1–1. https://doi.org/10.22261/JEA.PNCO7I
"""
import os
import yaml
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from maad import sound, util
from skimage.feature import peak_local_max

#%% Load configuration file
def load_config(config_file):
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    return config

#%% Function argument validation
def input_validation(data_input):
    """ Validate dataframe or path input argument """
    if isinstance(data_input, pd.DataFrame):
        pass
    elif isinstance(data_input, str):
        if os.path.isdir(data_input):
            print('Collecting metadata from directory path')
            df = util.get_metadata_dir(data_input)
        elif os.path.isfile(data_input) and data_input.lower().endswith(".csv"):
            print('Loading metadata from csv file')
            try:
                # Attempt to read all wav data from the provided file path.
                df = pd.read_csv(data_input) 
            except FileNotFoundError:
                raise FileNotFoundError(f"File not found: {data_input}")
    else:
        raise ValueError("Input 'data' must be either a Pandas DataFrame, a file path string, or None.")
    return df

#%%
def spectrogram_local_max(
    Sxx, tn, fn, ext,
    min_distance,
    threshold_abs,
    display=False,
    **kwargs
):
    """
    Find peaks on spectrogram as coordinate list in time and frequency

    Parameters
    ----------
    Sxx : ndarray
        Spectrogram of audio signal.
    tn : 1d array
        Time vector of target audio, which results from the maad.sound.spectrogram function.
    fn : 1d array
        Frecuency vector of target audio, which results from the maad.sound.spectrogram function.
    ext : list of scalars [left, right, bottom, top]
        Extent keyword arguments controls the bounding box in data coordinates for the spectrogram of the target audio, which results from the maad.sound.spectrogram function.
    min_distance : int
        Minimum number of time-frequency coefficients (or pixels) separating peaks. This parameter controls how close peaks can be to each other. Peaks that are closer than min_distance will be merged into a single peak.
    threshold_abs : float
        Minimum amplitude threshold for peak detection. Must be above Sxx.min().
    display : bool, optional
        Option to display the resulting figure.

    Returns
    -------
    peak_time: numpy.array
        The temporal coordinates of local peaks (maxima) in a spectrogram. 
    peak_frequency: numpy.array
        The spectral coordinates of local peaks (maxima) in a spectrogram.

    Examples
    --------
    >>> from maad import sound, rois
    >>> s, fs = sound.load('../data/spinetail.wav')
    >>> spectrogram_local_max( Sxx, tn, fn, ext, min_distance, threshold_abs, display=True)
    """

    # Validate input
    if threshold_abs is not None:
        if threshold_abs < Sxx.min():
            raise ValueError(f'Value for minimum peak amplitude is below minimum value on spectrogram')

    # Find peaks in spectrogram
    peaks = peak_local_max(
        Sxx, min_distance=min_distance, threshold_abs=threshold_abs, **kwargs
    )

    if display == True:
        fig, ax = plt.subplots(nrows=1, figsize=(10, 5))
        util.plot_spectrogram(Sxx, ext, log_scale=False, db_range=80, ax=ax)
        ax.scatter(
            tn[peaks[:, 1]],
            fn[peaks[:, 0]],
            marker="o",
            facecolor="none",
            edgecolor="yellow",
        )

    return tn[peaks[:, 1]], fn[peaks[:, 0]] 

#%%
def graphical_soundscape(
    data_input, target_fs, nperseg, noverlap, db_range, min_distance, threshold_abs
):
    """
    Computes a graphical soundscape from a given dataframe of audio files.

    Parameters
    ----------
    df : pandas DataFrame
        A Pandas DataFrame containing information about the audio files. The dataframe needs to have the columns 'path_audio' and 'time'.
    target_fs : int
        The target sample rate to resample the audio signal if needed.
    nperseg : int
        Window length of each segment to compute the spectrogram.
    noverlap : int
        Number of samples to overlap between segments to compute the spectrogram.
    db_range : float
        Dynamic range of the computed spectrogram.
    min_distance : int
        Minimum number of indices separating peaks.
    threshold_abs : float
        Minimum amplitude threshold for peak detection in decibels.

    Returns
    -------
    res : pandas DataFrame
        A Pandas DataFrame containing the graphical representation of the soundscape.
    """
    df = input_validation(data_input)
    res = pd.DataFrame()
    for idx, df_aux in df.iterrows():
        print(idx + 1, "/", len(df), ":", os.path.basename(df_aux.fname))
        
        # Load data
        s, fs = sound.load(df_aux.path_audio)
        s = sound.resample(s, fs, target_fs, res_type="scipy_poly")
        Sxx, tn, fn, ext = sound.spectrogram(s, fs, nperseg=nperseg, noverlap=noverlap)
        Sxx_db = util.power2dB(Sxx, db_range=db_range)

        # Compute local max
        peak_time, peak_freq = spectrogram_local_max(
            Sxx_db, tn, fn, ext,
            min_distance, 
            threshold_abs)
        
        # Count number of peaks at each frequency bin
        freq_idx, count_freq = np.unique(peak_freq, return_counts=True)
        count_peak = np.zeros(fn.shape)
        bool_index = np.isin(fn, freq_idx)
        indices = np.where(bool_index)[0]
        count_peak[indices] = count_freq / len(tn)
        peak_density = pd.Series(index=fn, data=count_peak)

        # Normalize per time
        #peak_density = (peak_density > 0).astype(int)
        peak_density.name = os.path.basename(df_aux.path_audio)
        res = pd.concat([res, peak_density.to_frame().T])

    res["time"] = df.time.str[0:2].astype(int).to_numpy()

    return res.groupby("time").mean()

#%%
def plot_graph(graph, ax=None, savefig=False, fname=None):
    """ Plots a graphical soundscape

    Parameters
    ----------
    graph : pandas.Dataframe
        A graphical soundscape as pandas dataframe with index as time and frequency as columns
    ax : matplotlib.axes, optional
        Axes for subplots. If not provided it creates a new figure, by default None.

    Returns
    -------
    ax
        Axes of the figure
    """
    if ax == None:
        fig, ax = plt.subplots()

    ax.imshow(graph.values.T, aspect='auto', origin='lower')
    ax.set_xlabel('Time (h)')
    ax.set_ylabel('Frequency (Hz)')
    ytick_idx = np.arange(0, graph.shape[1], 20).astype(int)
    ax.set_yticks(ytick_idx)
    ax.set_yticklabels(graph.columns[ytick_idx].astype(int).values)

    if savefig:
        plt.savefig(fname, bbox_inches='tight')
    
    return ax

#%%
# ----------------
# Main Entry Point
# ----------------
def main():
    parser = argparse.ArgumentParser(
        description="Compute graphical soundscape on audio data.")
    parser.add_argument(
        "operation", 
        choices=[
            "spectrogram_local_max",
            "graphical_soundscape",
            "plot_graph",
        ],
        help="Graphical soundscape operation")
    
    parser.add_argument("--input_file", type=str, help="Input file")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--display", "-d", action="store_true", help="Enable to display plot")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose mode")
    args = parser.parse_args()
    
    config_file = args.config
    config = load_config(config_file)
    # Load configuration
    #path_data = args.config["preprocessing"]["path_save_metadata_clean"]
    target_fs = config["graph_soundscapes"]["target_fs"]
    nperseg = config["graph_soundscapes"]["nperseg"]
    noverlap = config["graph_soundscapes"]["noverlap"]
    db_range = config["graph_soundscapes"]["db_range"]
    min_distance = config["graph_soundscapes"]["min_distance"]
    threshold_abs = config["graph_soundscapes"]["threshold_abs"]

    if args.operation == "spectrogram_local_max":
        s, fs = sound.load(args.input_file)
        s = sound.resample(s, fs, target_fs, res_type="scipy_poly")
        Sxx, tn, fn, ext = sound.spectrogram(s, fs, nperseg=nperseg, noverlap=noverlap)
        Sxx_db = util.power2dB(Sxx, db_range=db_range)
        result = spectrogram_local_max(Sxx_db, tn, fn, ext, min_distance, 
                                       threshold_abs, display=args.display)
        print(result)

    elif args.operation == "graphical_soundscape":
        result = graphical_soundscape(args.path, args.recursive, args.verbose)

if __name__ == "__main__":
    main()
