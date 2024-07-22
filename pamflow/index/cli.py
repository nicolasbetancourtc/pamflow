#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitary functions to manage, check and preprocess large sampling data assiciated with passive acoustic monitoring

"""
import os
import glob
import argparse
import matplotlib.pyplot as plt
import pandas as pd
import yaml
from scipy.spatial.distance import pdist
import numpy as np

def load_config(file_path):
    with open(file_path, 'r') as config_file:
        config = yaml.safe_load(config_file)
    return config

def compute_index(sample, distance_metric, template_forest, template_grassland):
    dist_forest = pdist([sample, template_forest], metric=distance_metric)
    dist_grassland = pdist([sample, template_grassland], metric=distance_metric)
    return dist_grassland[0] - dist_forest[0]
    
def validate_graph(path):
    sample = pd.read_csv(path)
    sample.drop(columns=['time'], inplace=True)
    return pd.Series(sample.values.ravel())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute Biotic Acoustic Integrity (BAI)")
    parser.add_argument("--input", "-i", 
                        type=str, help="Path to directory to search")
    parser.add_argument("--output", "-o", 
                        type=str, help="Path and filename to save results")
    parser.add_argument("--config", "-c", type=str, default='config.yaml',
                        help="Path to configuration file")
    parser.add_argument("--distance", "-d", type=str, default='cosine',
                        help="Distance metric to compute index: 'cosine' or 'braycurtis'")
    args = parser.parse_args()

    # Load configuration
    distance_metric = args.distance
    config_file = args.config
    config = load_config(config_file)
    template_forest = config["index"]["template_forest"]
    template_grassland = config["index"]["template_grassland"]


    # load templates
    print('Computing index values...')
    forest = pd.read_csv(template_forest)['Forest']
    grassland = pd.read_csv(template_grassland)['Grassland']
    if os.path.isfile(args.input):
        # load sample
        sample = validate_graph(args.input)
        # compute index value
        idx_val = compute_index(sample, distance_metric, forest, grassland)
        print(f'Index value for file {os.path.basename(args.input)}: {idx_val}')

    elif os.path.isdir(args.input):
        flist = glob.glob(os.path.join(args.input, '*.csv'))
        df = dict()
        for graph in flist:
            sample = validate_graph(graph)
            # compute index value
            idx_val = compute_index(sample, distance_metric, forest, grassland)
            df[os.path.basename(graph)] = idx_val
        df = pd.DataFrame(df.items(), columns=['fname', 'index_value'])
        df.to_csv(args.output, index=False)
        print(f'Results saved at {args.output}')

    else:
        print("Path does not exist or is not accessible.")
    
