import os
import subprocess
import pytest

MODEL_PATH = "artifacts/model.joblib"
METRICS_PATH = "metrics.txt"
DATA_PATH = "data/iris.csv"

@pytest.fixture(scope="module")
def pipeline_run():
    """
    A fixture to run the entire train.py script before tests.
    It also handles cleaning up the artifacts after the tests are done.
    
    'scope="module"' means this will only run ONCE for all tests in this file.
    """

    result = subprocess.run(
        ["python", "train.py"], 
        capture_output=True, 
        text=True,
        check=True
    )
    
    yield
    
    print("\nCleaning up generated artifacts...")
    if os.path.exists(MODEL_PATH):
        os.remove(MODEL_PATH)
    if os.path.exists(METRICS_PATH):
        os.remove(METRICS_PATH)


# --- Test 1: Data Validation Test ---
def test_source_data_exists():
    """A simple check to ensure the input data is where we expect it to be."""
    assert os.path.exists(DATA_PATH), f"Input data not found at {DATA_PATH}"


# --- Test 2: Evaluation Test (Artifact Creation) ---
def test_artifacts_are_created(pipeline_run):
    """
    Checks if the script successfully created the model and metrics files.
    """
    assert os.path.exists(MODEL_PATH), "Model file was not created by train.py"
    assert os.path.exists(METRICS_PATH), "Metrics file was not created by train.py"


# --- Test 3: Evaluation Test (Model Performance) ---
def test_model_performance(pipeline_run):
    """
    Reads the generated metrics file and checks if the accuracy meets 
    our minimum standard.
    """
    assert os.path.exists(METRICS_PATH), "Metrics file must exist to check performance."
    
    try:
        with open(METRICS_PATH, "r") as f:
            content = f.read()
        
        accuracy_value = float(content.split(":")[1].strip())
        print(f"Found accuracy: {accuracy_value}")
        
        assert accuracy_value > 0.85, f"Model accuracy {accuracy_value} is below the 0.85 threshold."

    except (ValueError, IndexError):
        pytest.fail(f"Could not parse accuracy from metrics.txt. Check its format. Content was: '{content}'")