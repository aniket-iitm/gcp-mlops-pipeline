import os
import pytest
import json
import joblib         # <-- ADD THIS IMPORT
import pandas as pd     # <-- ADD THIS IMPORT

# Define the paths to the ARTIFACTS that the CI pipeline should have created
MODEL_PATH = "artifacts/model.joblib"
METRICS_PATH = "metrics.txt"

# --- Test 1: Artifacts Existence Test ---
# This test is good. It validates that the main 'Run training script' step
# in our workflow was successful.

def test_artifacts_were_created():
    """
    Checks if the training script (run in a previous CI step)
    successfully created the model and metrics files.
    """
    assert os.path.exists(MODEL_PATH), f"Model artifact not found at {MODEL_PATH}. Did the training step fail?"
    assert os.path.exists(METRICS_PATH), f"Metrics file not found at {METRICS_PATH}. Did the training step fail?"

# --- Test 2: Model Performance Test ---
# This test now has a dual purpose: assert accuracy AND save results for plotting
def test_model_performance_and_save_results():
    """
    Reads the metrics, asserts accuracy, and saves prediction results for plotting.

    """
    # First, ensure the metrics file is actually there before trying to read it.
    assert os.path.exists(METRICS_PATH), "Metrics file must exist to check performance."
    
    # --- Part 1: Rerunning prediction to get true/pred values ---
    # Load the model that was created by the train.py step in the CI workflow.
    model = joblib.load(MODEL_PATH)
    
    # Load the data that was used for training (the poisoned data).
    data = pd.read_csv("data/iris_poisoned.csv")
    
    # Separate features and the true (potentially poisoned) labels
    X_test = data[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]
    y_true = data['species']
    
    # Make predictions with the loaded model
    y_pred = model.predict(X_test)
    
    # --- Part 2: Read accuracy from the metrics file and assert ---
    try:
        with open(METRICS_PATH, "r") as f:
            content = f.read()
        
        # Parse the accuracy value from the file
        accuracy_value = float(content.split(":")[1].strip())
        print(f"Found accuracy from CI run: {accuracy_value}")
        
        # --- Part 3: Save results to a file for the plotting script ---
        results_data = {
            'y_true': y_true.tolist(),
            'y_pred': y_pred.tolist(),
            'accuracy': accuracy_value
        }
        with open('test_results.json', 'w') as f:
            json.dump(results_data, f)
        print("Test results saved to test_results.json for plotting.")

        # --- Part 4: The assertion (our quality gate) ---

        assert accuracy_value >= 0.85, f"Model accuracy {accuracy_value} is below the 0.85 threshold."

    except (ValueError, IndexError):
        pytest.fail(f"Could not parse accuracy from metrics.txt. Check its format.")