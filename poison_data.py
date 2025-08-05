import pandas as pd
import numpy as np
import argparse
import os

# Define the paths
SOURCE_DATA_PATH = 'data/iris.csv'
POISONED_DATA_PATH = 'data/iris_poisoned.csv'

def poison_data(poison_level: float):
    """
    Loads the original Iris dataset, poisons a specified percentage of the labels,
    and saves the new dataset.

    Args:
        poison_level (float): The fraction of data to poison (e.g., 0.1 for 10%).
    """
    print(f"--- Starting Data Poisoning ---")
    
    if not 0 <= poison_level <= 1:
        raise ValueError("Poison level must be between 0 and 1.")

    # If the poison level is 0, just copy the original file and exit
    if poison_level == 0:
        print("Poison level is 0. Using original data.")
        df = pd.read_csv(SOURCE_DATA_PATH)
        df.to_csv(POISONED_DATA_PATH, index=False)
        print(f"Original data copied to {POISONED_DATA_PATH}")
        return

    print(f"Loading original data from {SOURCE_DATA_PATH}")
    df = pd.read_csv(SOURCE_DATA_PATH)
    
    # Get the unique species labels
    labels = df['species'].unique()
    num_labels = len(labels)
    
    # Determine the number of rows to poison
    num_rows_to_poison = int(len(df) * poison_level)
    print(f"Poisoning {num_rows_to_poison} rows ({poison_level:.0%}) of the data.")
    
    # Get random indices to poison
    poison_indices = np.random.choice(df.index, size=num_rows_to_poison, replace=False)
    
    # For each poisoned row, flip the label to a different, random one
    for idx in poison_indices:
        original_label = df.loc[idx, 'species']
        # Create a list of other possible labels
        other_labels = list(filter(lambda l: l != original_label, labels))
        # Choose a new, incorrect label at random
        new_label = np.random.choice(other_labels)
        df.loc[idx, 'species'] = new_label
        
    print(f"Saving poisoned data to {POISONED_DATA_PATH}")
    df.to_csv(POISONED_DATA_PATH, index=False)
    print("--- Data Poisoning Complete ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Poison the Iris dataset labels.")
    parser.add_argument(
        "--level",
        type=float,
        required=True,
        help="The fraction of data to poison (e.g., 0.05 for 5%)."
    )
    args = parser.parse_args()
    poison_data(args.level)