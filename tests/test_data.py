import os
import pytest

# Define the paths to the ARTIFACTS that the CI pipeline should have created
MODEL_PATH = "artifacts/model.joblib"
METRICS_PATH = "metrics.txt"

# --- REMOVED THE FIXTURE ---
# We no longer need a fixture to run train.py. The CI workflow is responsible for that.
# Our tests will now check the outputs of the main workflow steps.

# --- Test 1: Artifacts Existence Test ---
# This is now the most important test. It validates that the main
# 'Run training script' step in our workflow was successful.
def test_artifacts_were_created():
    """
    Checks if the training script (run in a previous CI step)
    successfully created the model and metrics files.
    """
    assert os.path.exists(MODEL_PATH), f"Model artifact not found at {MODEL_PATH}. Did the training step fail?"
    assert os.path.exists(METRICS_PATH), f"Metrics file not found at {METRICS_PATH}. Did the training step fail?"

# --- Test 2: Model Performance Test ---
# This test depends on the artifacts existing, so it should run after the first test.
def test_model_performance_against_threshold():
    """
    Reads the metrics file created by the CI training step and checks if the
    accuracy meets our minimum standard. This test is EXPECTED to fail on poisoned data.
    """
    # First, ensure the metrics file is actually there before trying to read it.
    assert os.path.exists(METRICS_PATH), "Metrics file must exist to check performance."
    
    try:
        with open(METRICS_PATH, "r") as f:
            content = f.read()
        
        # Parse the accuracy value from the file
        accuracy_value = float(content.split(":")[1].strip())
        print(f"Found accuracy from CI run: {accuracy_value}")
        
        # This assertion is our quality gate. It will PASS for the 0% run and FAIL for others.
        assert accuracy_value > 0.85, f"Model accuracy {accuracy_value} is below the 0.85 threshold."

    except (ValueError, IndexError):
        pytest.fail(f"Could not parse accuracy from metrics.txt. Check its format. Content was: '{content}'")