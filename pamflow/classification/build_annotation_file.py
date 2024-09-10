""" 
Load BirdNET segments and build annotation file for expert validation

"""
import glob
import os
import pandas as pd
import argparse

def list_directories(path):
    directories = []
    for entry in os.listdir(path):
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            directories.append(full_path)
    return directories

def find_csv_files(directory):
    # Check if there are any subdirectories
    subdirs = [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]
    
    if subdirs:
        # Search in directory and all subdirectories
        csv_files = glob.glob(os.path.join(directory, '**', '*.wav'), recursive=True)
    else:
        # Search only in the directory
        csv_files = glob.glob(os.path.join(directory, '*.wav'))
    
    return csv_files

def build_annotation_file(input_dir, output_dir):
    """
    Build an annotation CSV file to validate BirdNET segments.

    Parameters:
    - input_dir (str): Directory where the BirdNET segments (.wav files) are stored.
    - output_dir (str): Path where the output CSV file will be saved.
    """
    list_dirs = list_directories(input_dir)
    for directory in list_dirs:
        dir_name = os.path.basename(directory)
        df = pd.DataFrame(find_csv_files(directory), columns=['path'])
        
        # Process data
        df['segment'] = df.path.apply(os.path.basename)
        df['birdnet_conf'] = df.segment.str.split('_').str[0].astype(float)
        df['filename'] = (df.segment.str.split('_').str[2] + '_' +
                        df.segment.str.split('_').str[3] + '_' +
                        df.segment.str.split('_').str[4] + '.WAV')
        df['start_time(s)'] = df.segment.str.split('_').str[5].str[:-1].astype(float)
        df['end_time(s)'] = df.segment.str.split('_').str[6].str[:-5].astype(float)
        df['species'] = df.path.str.split('/').str[-2]
        df.sort_values(['segment'], inplace=True)
        df.drop(columns=['path'], inplace=True)

        # Save dataframe to file
        output_file = os.path.join(output_dir, f'annot_segments_{dir_name}.csv')
        df.to_csv(output_file, index=False)
        print(f"Annotation file saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Build annotation file to validate BirdNET segments.')
    parser.add_argument('-i', '--input', required=True, help='Directory where the segments are stored.')
    parser.add_argument('-o', '--output', help='Path where the CSV file will be saved.')

    args = parser.parse_args()
    
    # Set output to input if output is not provided
    output_dir = args.output if args.output else args.input

    build_annotation_file(args.input, output_dir)
