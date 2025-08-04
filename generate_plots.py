import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import json
import argparse
import os

# Create a directory to save plots if it doesn't exist
os.makedirs('plots', exist_ok=True)

def plot_results(poison_level):
    """
    Generates and saves a confusion matrix and a simple accuracy report image
    based on the results of the training run.
    """
    try:
        # --- 1. Generate Confusion Matrix ---
        # Load the predictions made during the last test run
        # We need to save these from our test script first (see next step)
        with open('test_results.json', 'r') as f:
            results = json.load(f)
        
        y_true = results['y_true']
        y_pred = results['y_pred']
        accuracy = results['accuracy']
        labels = sorted(list(set(y_true)))

        # Create confusion matrix
        cm = pd.crosstab(pd.Series(y_true, name='Actual'), pd.Series(y_pred, name='Predicted'))
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=labels, yticklabels=labels)
        plt.title(f'Confusion Matrix (Poison Level: {poison_level}%)')
        
        # Save the plot to a file
        cm_path = f'plots/confusion_matrix_{poison_level}.png'
        plt.savefig(cm_path)
        plt.close()
        print(f"Confusion matrix saved to {cm_path}")

        # --- 2. Generate Accuracy Bar Chart ---
        # We'll just create a simple bar chart showing the single accuracy value
        plt.figure(figsize=(6, 4))
        sns.barplot(x=['Accuracy'], y=[accuracy])
        plt.ylim(0, 1.0)
        plt.title(f'Model Accuracy (Poison Level: {poison_level}%)')
        plt.ylabel('Accuracy Score')
        
        # Add the accuracy value on top of the bar
        plt.text(0, accuracy + 0.05, f'{accuracy:.3f}', ha='center', va='bottom', fontsize=12)

        acc_path = f'plots/accuracy_chart_{poison_level}.png'
        plt.savefig(acc_path)
        plt.close()
        print(f"Accuracy chart saved to {acc_path}")

    except FileNotFoundError:
        print("Warning: test_results.json not found. Skipping plot generation.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate plots from test results.")
    parser.add_argument(
        "--poison-level",
        type=int,
        required=True,
        help="The integer poison level percentage (e.g., 5)."
    )
    args = parser.parse_args()
    plot_results(args.poison_level)