import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

# Create the FastAPI app object
app = FastAPI()

# Define the input data schema using Pydantic
class IrisInput(BaseModel):
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float

# The path to the model artifact inside the Docker container
MODEL_PATH = "artifacts/model.joblib"

# Load the trained model when the app starts
model = joblib.load(MODEL_PATH)

@app.get("/")
def read_root():
    return {"message": "Iris Classifier API (Simple) is running!"}

@app.post("/predict")
def predict_species(iris_input: IrisInput):
    """
    Takes Iris features as input and returns the predicted species name directly.
    """
    # Convert input data to a pandas DataFrame
    input_data = pd.DataFrame([iris_input.dict()])
    
    # Make a prediction. The model now directly outputs the species name.
    prediction = model.predict(input_data)[0]
    
    # Get the probabilities for each class
    probabilities = model.predict_proba(input_data)[0]
    
    # Get the class names from the model
    class_names = model.classes_
    
    # Create a dictionary of class probabilities
    confidence_scores = {class_names[i]: float(probabilities[i]) for i in range(len(class_names))}
    
    return {
        "predicted_species": prediction,
        "confidence_scores": confidence_scores
    }