#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitary functions to manage, check and preprocess large sampling data assiciated with passive acoustic monitoring

"""
import os
import argparse
import shutil
import pandas as pd
import numpy as np
import glob
import yaml
from pathlib import Path
from os import listdir
from maad import sound, util
import matplotlib.pyplot as plt
import seaborn as sns

# ----------------------------------
# Main Utilities For Other Functions
# ----------------------------------
#%% Load configuration file
def load_config(config_file):
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    return config

#%% Function argument validation
def input_validation(data_input):
    """ Validate dataframe or path input argument """
    if isinstance(data_input, pd.DataFrame):
        return data_input

    elif isinstance(data_input, str):
        if os.path.isdir(data_input):
            print('Collecting metadata from directory path')
            return util.get_metadata_dir(data_input, verbose=True)
        elif os.path.isfile(data_input) and data_input.lower().endswith(".csv"):
            print('Loading metadata from csv file')
            try:
                return pd.read_csv(data_input) 
            except FileNotFoundError:
                raise FileNotFoundError(f"File not found: {data_input}")
    
    else: 
        raise ValueError("Input 'data' must be either a Pandas DataFrame, a file path string, or None.")

def date_validation(date_str):
    try:
        return pd.to_datetime(date_str, format="%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid date format. Use 'YYYY-MM-DD'.")
    
#%%
# ------------------------
# Visualization Functions
# ------------------------
def plot_sensor_deployment(df, x='sensor_name', y='date', ax=None):
    """ Plot sensor deployment to have an overview of the sampling

    Parameters
    ----------
    df : pandas DataFrame
        The dataframe must have the columns site, date, sample_length.
        Use maad.util.get_audio_metadata to compile the dataframe.
    ax : matplotlib.axes, optional
        Matplotlib axes fot the figure, by default None

    Returns
    -------
    matplotlib.figure
        If axes are not provided, a figure is created and figure handles are returned.
    """
    # Function argument validation
    df = input_validation(df)
    
    # Group recordings by day
    df['date'] = pd.to_datetime(df['date']).dt.date
    df_out = df.groupby(['sensor_name', 'date']).size().reset_index(name='count')
    df_out.sort_values(by=['sensor_name', 'date'], inplace=True)
    
    # Reorder sites according to first recording
    # Calculate the first date for each site
    first_date_per_site = df_out.groupby('sensor_name')['date'].min().reset_index()
    first_date_per_site = first_date_per_site.rename(columns={'date': 'first_date'})

    # Merge the first date information back to the original DataFrame
    df_out = df_out.merge(first_date_per_site, on='sensor_name')

    # Sort the DataFrame based on the first date
    df_out = df_out.sort_values(by='first_date')

    # Plot dataframe
    if ax == None:
        _, ax = plt.subplots(figsize=[8,5])

    if df_out['count'].nunique() == 1:    
        sns.scatterplot(y=y, x=x, size='count', hue='count', data=df_out, ax=ax,
                        hue_norm=(0, df_out['count'].max()),
                        size_norm=(0, df_out['count'].max()))
    else:
        sns.scatterplot(y=y, x=x, size='count', hue='count', data=df_out, ax=ax)
        
    ax.grid(alpha=0.2)
    ax.set_title(
        f'Sensor Deployment: {df.sensor_name.unique().shape[0]} sites | {df.shape[0]} files')
    plt.xticks(rotation=45)
    plt.legend(
        bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0, title='N. Rec')
    plt.tight_layout()
    plt.show()

#%%
# ------------------------
# File Managment Functions
# ------------------------
def search_files(directory=".", extension=""):
    """
    Search for files within a specified directory and its subdirectories.

    Args:
        directory (str, optional): The directory to start the search in (default: current directory).
        extension (str, optional): The file extension to filter by (e.g., ".txt"). If provided, only files with
            this extension will be considered. If not provided or an empty string, all files will be considered.

    Returns:
        str or None: The path to the first matching file found, or None if no matching file is found.

    Note:
        This function uses a recursive approach to search for files in the specified directory and its subdirectories.
        It returns the path to the first matching file it encounters during the search.
    """
    extension = extension.lower()
    for dirpath, dirnames, files in os.walk(directory):
        for name in files:
            if extension and name.lower().endswith(extension):
                return os.path.join(dirpath, name)
            elif not extension:
                return os.path.join(dirpath, name)

def listdir_pattern(path_dir, ends_with=None):
    """
    Wraper function from os.listdir to include a filter to search for patterns
    
    Parameters
    ----------
        path_dir: str
            path to directory
        ends_with: str
            pattern to search for at the end of the filename
    Returns
    -------
    """
    flist = listdir(path_dir)

    new_list = []
    for names in flist:
        if names.endswith(ends_with):
            new_list.append(names)
    return new_list

def build_folder_structure(root_dir):
    # Define the subdirectories
    subdirs = [
        "input",
        "input/sensor_deployment",
        "input/mannot",
        "output",
        "output/figures",
        "output/metadata",
        "output/graphical_soundscapes",
        "output/acoustic_indices",
        "output/timelapse",
        "output/birdnet"
    ]

    # Create the root directory if it doesn't exist
    if not os.path.exists(root_dir):
        os.makedirs(root_dir)

    # Create subdirectories
    for subdir in subdirs:
        subdir_path = os.path.join(root_dir, subdir)
        if not os.path.exists(subdir_path):
            os.makedirs(subdir_path)

    # Create README.md file
    readme_path = os.path.join(root_dir, "README.md")
    if not os.path.exists(readme_path):
        with open(readme_path, "w") as readme_file:
            readme_file.write("")

    print("Folder structure created successfully.")

#%%
def find_wav_files(folder_path, recursive=False):
    """ Search for files with wav or WAV extension """
    wav_files = []
    if recursive:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.wav'):
                    wav_files.append(os.path.join(root, file))
    else:
        for file in os.listdir(folder_path):
                    if file.lower().endswith('.wav'):
                        wav_files.append(os.path.join(folder_path, file))
    
    # Transform the list of strings to a list of Path objects
    wav_files = [Path(path) for path in wav_files]
    
    return wav_files

#%%
def find_files(folder_path, endswith='*', recursive=False):
    """ Search for files with any extension """
    files = []
    if recursive:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(endswith):
                    files.append(os.path.join(root, file))
    else:
        for file in os.listdir(folder_path):
                    if file.lower().endswith(endswith):
                        files.append(os.path.join(folder_path, file))
    
    # Transform the list of strings to a list of Path objects
    files = [Path(path) for path in files]
    
    return files

#%%
def add_file_prefix(folder_name: str, recursive:bool=False, verbose:bool=False) -> None:
    """
    Adds a prefix to the file names in the given directory.
    The prefix is the name of the immediate parent folder of the files.

    Parameters:
    folder_name(str): Name of directory which contains files.
    recursive(bool): If True, searches for files in sub-directories recursively.
                     Defaults to False if not provided.

    Returns: None
    """
    folder_path = Path(folder_name)

    # Get list of files to process
    flist = find_wav_files(folder_path, recursive=recursive)
    
    # remove hidden files 
    flist = [f for f in flist if not f.name.startswith('.')]

    if verbose:
        print(f'Number of WAVE files detected: {len(flist)}')

    # remove files that already have the parent directory name
    flist = [f for f in flist if (not f.name.startswith(f.parent.name+'_'))]

    # Loop and change names
    if verbose:
        print(f'Number of WAVE files detected with no prefix: {len(flist)}')
        print('Renaming files...')
    
    flist_changed = list()
    for fname in flist:
        prefix = fname.parent.name
        new_fname = fname.with_name(f'{prefix}_{fname.name}')
        try:
            fname.rename(new_fname)
            flist_changed.append(str(new_fname))
        except Exception as e:
            print(f"Error occurred while renaming {fname}: {e}")
    
    if verbose:
        print('Process completed!')
        print(f'Number of WAVE files renamed: {len(flist_changed)}')
        
    return flist_changed

def copy_file_list(flist, path_save):
    """ Copy selected files to a new folder """
    for _, row in flist.iterrows():
        src_file = row.path_audio
        dst_file = path_save + row.fname
        shutil.copyfile(src_file, dst_file)

def rename_files_time_delay(path_dir, delay_hours=-5, verbose=False):
    """ Rename files to fix time delay issues
    When using audio recorders, time can be badly configured. This simple function allows to fix time dalys that occurr because of changes in time zones. The files must have a standard format.

    """
    if type(path_dir) == str:
        flist = glob.glob(os.path.join(path_dir, '*.WAV'))
        flist.sort()

    for fname in flist:
        fname_orig = util.filename_info(fname)
        date_orig = pd.to_datetime(fname_orig['date'])
        fname_ext = '.' + fname_orig['fname'].split('.')[1]
        date_fixed = date_orig + pd.Timedelta(hours=delay_hours)
        fname_fixed = fname_orig['sensor_name']+'_'+date_fixed.strftime('%Y%m%d_%H%M%S')+fname_ext
        if verbose:
            print(f'Renaming file: {os.path.basename(fname)} > {fname_fixed}')
        
        # rename file
        os.rename(src=fname, dst=os.path.join(os.path.dirname(fname), fname_fixed))

#%%
# ------------------------
# Audio Metadata Functions
# ------------------------

def print_damaged_files(df):
    for _, row in df.iterrows():
        try:
            util.audio_header(row.path_audio)
        except:
            print(row.fname)

def random_sample_metadata(df, n_samples_per_site=10, hour_sel=None, random_state=None):
    """ Get a random sample form metadata DataFrame """
    if hour_sel==None:
        hour_sel = [str(i).zfill(2) for i in range(24)]

    # format data
    df.loc[:,'hour'] = df.loc[:,'date'].str[11:13].astype(str)
    sensor_list = df.sensor_name.unique()

    # Batch process
    df_out = pd.DataFrame()
    for sensor_name in sensor_list:
        df_sel = df.loc[(df.sensor_name==sensor_name) & (df.hour.isin(hour_sel)),:]
        df_sel = df_sel.sample(n_samples_per_site, random_state=random_state)
        df_out = pd.concat([df_out, df_sel])

    df_out.reset_index(drop=True, inplace=True)

    return df_out

def metadata_summary(df):
    """ Get a summary of a metadata dataframe of the acoustic sampling

    Parameters
    ----------
    df : pandas DataFrame or string with path to a csv file
        The dataframe must have the columns site, date, sample_length.
        Use maad.util.get_audio_metadata to compile the dataframe.

    Returns
    -------
    pandas DataFrame
        A summary of each site
    """
    # Function argument validation
    df = input_validation(df)
        
    df['date'] = pd.to_datetime(df.date,  format='%Y-%m-%d %H:%M:%S')
    df.dropna(inplace=True)
    df_summary = {}
    for site, df_site in df.groupby('sensor_name'):
        site_summary = {
            'date_ini': str(df_site.date.min()),
            'date_end': str(df_site.date.max()),
            'n_recordings': len(df_site),
            'duration': str(df_site.date.max() - df_site.date.min()),
            'time_diff': df_site['date'].sort_values().diff().median(),
            'sample_length': round(df_site.length.median(), 1),
            'sample_rate': int(df_site.sample_rate.median()),
        }
        df_summary[site] = site_summary
    df_summary = pd.DataFrame(df_summary).T
    return df_summary.reset_index().rename(columns={'index': 'sensor_name'})

#%%
# --------------------
# Time Lapse Functions
# --------------------
def concat_audio(flist, sample_len=1, verbose=False, display=False):
    """ Concatenates samples using a list of audio files

    Parameters
    ----------
    flist : list or pandas Series
        List of files to concatenate
    sample_len : float, optional
        Length in seconds of each sample, default is 1 second
    display : bool, optional
        If true displays the audio spectrogram, by default False
    
    Return
    ------
    """
    
    # Compute long wav
    long_wav = list()
    for idx, fname in enumerate(flist, start=1):
        if verbose:
            print(f'{idx} / {len(flist)} : {os.path.basename(fname)}', end='\r')
        s, fs = sound.load(fname)
        s = sound.trim(s, fs, 0, sample_len)
        long_wav.append(s)

    long_wav = np.concatenate(long_wav)
    
    # Plot
    if display:
        Sxx, tn, fn, ext = sound.spectrogram(
            long_wav, fs, window='hann', nperseg=1024, noverlap=512)
        fig, ax = plt.subplots(1,1, figsize=(10,3))
        util.plot_spectrogram(Sxx, extent=[0, 24, 0, 11],
                            ax=ax, db_range=80, gain=25, colorbar=False)
        ax.set_xlabel('Time [Hours]')
        ax.set_xticks(range(0,25,4))

    return long_wav, fs

def audio_timelapse(
        data, sample_len, sample_period='30T', date_range=None, path_save=None, save_audio=True, verbose=True)  -> None:
    """ Build audio timelapse """
    
    # Function argument validation
    df = input_validation(data)
    date_range = [date_validation(date_range[0]), date_validation(date_range[1])]

    # select files to create timelapse
    df.date = pd.to_datetime(df.date)
    idx_dates = df.date.between(date_range[0], date_range[1], inclusive='left')
    df_timelapse = df.loc[idx_dates,:]
    df_timelapse['day'] = df_timelapse.date.dt.date
    df_timelapse.set_index('date', inplace=True)
    ngroups = df_timelapse.groupby(['sensor_name', 'day']).ngroups

    # create time lapse
    print(f'Processing {ngroups} groups:')
    for site, df_site in df_timelapse.groupby('sensor_name'):
        print(site)
        df_site.sort_values('date', inplace=True)
        df_site = df_site.resample(sample_period).first()
        df_site.dropna(inplace=True)
        long_wav, fs = concat_audio(df_site['path_audio'],
                                    sample_len=sample_len, 
                                    verbose=verbose)
        if save_audio:
            #print(type(date_range[0]))
            #print(date_range[0])
            date_ini_str = date_range[0].strftime('%Y%m%d')
            date_end_str = date_range[1].strftime('%Y%m%d')
            sound.write(os.path.join(path_save, f'{site}_timelapse_{date_ini_str}_{date_end_str}.wav'), fs, long_wav, bit_depth=16)
        print('\n')
        
#%%
def plot_spectrogram(fname, nperseg=1024, noverlap=0.5, db_range=80, width=10, height=4):
    s, fs = sound.load(fname)
    Sxx, tn, fn, ext = sound.spectrogram(
        s, fs, nperseg=nperseg, noverlap=nperseg*noverlap)
    util.plot_spectrogram(Sxx, ext, db_range, figsize=(height,width), colorbar=False)

#%%
def select_metadata(input_path, sensor_name=None, date_range=None):
    df = input_validation(input_path)
    
    if sensor_name is None and date_range is None:
        return df    
    
    else: 
        if sensor_name is not None:
            idx_keep = df.sensor_name.isin(sensor_name)
        
        if date_range is not None:
            date_range = [date_validation(date_range[0]), date_validation(date_range[1])]
            df.date = pd.to_datetime(df.date)
            idx_dates = df.date.between(date_range[0], date_range[1], inclusive='left')
            idx_keep = (idx_keep & idx_dates)
        
        return df.loc[idx_keep,:]
