import pandas as pd
import os
import glob
import argparse
from utils import merge_annot_files
import matplotlib.pyplot as plt
import seaborn as sns

def load_and_filter_data(path_annot, min_conf):
    """
    Load and filter annotation files based on the minimum confidence threshold.

    Parameters:
    path_annot (str): Path to the annotation files.
    min_conf (float): Minimum confidence threshold.

    Returns:
    pd.DataFrame: Filtered dataframe with confidence above the threshold.
    """
    flist = glob.glob(os.path.join(path_annot, '**', '*.csv'), recursive=True)
    df = merge_annot_files(flist, rtype='csv')
    df['Confidence'] = (df['Confidence'] >= min_conf).astype(int)
    return df.loc[df.Confidence == 1]

def create_abundance_matrix(df_clean, path_save_matrix, min_conf):
    """
    Create the species abundance matrix and save it as a CSV.

    Parameters:
    df_clean (pd.DataFrame): Filtered dataframe with valid detections.
    path_save_matrix (str): Path to save the abundance matrix.
    min_conf (float): Minimum confidence threshold.
    """
    pivot_table = pd.pivot_table(
        df_clean, index='Fname', columns='Scientific name', 
        values='Confidence', aggfunc='sum', fill_value=0
    )
    pivot_table.index = pivot_table.index.str.replace('.BirdNET.results.csv', '.WAV')
    pivot_table.to_csv(os.path.join(path_save_matrix, f'file_spmatrix_{min_conf}conf.csv'))

    pivot_table['sensor_name'] = pivot_table.index.str.split('_').str[0].values
    pivot_table_site = pivot_table.groupby('sensor_name').sum()
    pivot_table_site.to_csv(os.path.join(path_save_matrix, f'site_spmatrix_{min_conf}conf.csv'))

def plot_species(df_clean, path_save_matrix, min_conf):
    """
    Plot species detections and save the plot as an image.

    Parameters:
    df_clean (pd.DataFrame): Filtered dataframe with valid detections.
    path_save_matrix (str): Path to save the plot.
    min_conf (float): Minimum confidence threshold.
    """
    plt_data = df_clean['Scientific name'].value_counts()
    plt_data = plt_data.loc[plt_data > 30]

    fig, ax = plt.subplots(figsize=(8, 15))
    bars = ax.barh(plt_data.index, plt_data.values)

    # Add text with values for each bar
    for bar in bars:
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2, '{:d}'.format(int(width)),
                va='center', ha='left', fontsize=10)

    ax.set_title(f'{len(plt_data)} species detected with threshold {min_conf}')
    ax.grid(axis='x', color='white')
    plt.tight_layout()
    sns.despine(trim=True)

    # Save the plot
    plot_path = os.path.join(path_save_matrix, f'species_plot_{min_conf}conf.png')
    plt.savefig(plot_path)

def main():
    # Set up the argument parser
    parser = argparse.ArgumentParser(description="Generate species abundance matrix from BirdNET detections")
    parser.add_argument('--input', '-i', type=str, required=True, help='Path to BirdNET detection files (input folder)')
    parser.add_argument('--output', '-o', type=str, required=True, help='Path to save the abundance matrix (output folder)')
    parser.add_argument('--min_conf', '-min_conf', type=float, required=True, help='Minimum confidence threshold for detections')

    # Parse the arguments
    args = parser.parse_args()
    path_annot = args.input
    path_save_matrix = args.output
    min_conf = args.min_conf

    # Step 1: Load and filter the data
    print('Loading annotations...')
    df_clean = load_and_filter_data(path_annot, min_conf)
    print(f'Done! {len(df_clean)} detections found with minimum confidence {min_conf}')

    # Step 2: Create abundance matrix and save to file
    print('Saving species matrices...')
    create_abundance_matrix(df_clean, path_save_matrix, min_conf)

    # Step 3: Plot species and save the plot
    print('Plotting filtered species detections')
    plot_species(df_clean, path_save_matrix, min_conf)

if __name__ == "__main__":
    main()
