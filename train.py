# train.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn import metrics
import joblib
import os

DATA_PATH = 'data/iris.csv'
MODEL_DIR = 'artifacts'
MODEL_NAME = 'model.joblib'
METRICS_FILE = 'metrics.txt'
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_NAME)

def train_and_evaluate():
    """
    This function loads data, trains the model, evaluates it,
    and saves artifacts. It returns the model's accuracy.
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    print(f"Loading data from {DATA_PATH}...")
    try:
        data = pd.read_csv(DATA_PATH)
    except FileNotFoundError:
        print(f"Error: {DATA_PATH} not found.")
        exit(1)
    print("Data loaded successfully.")

    print("Splitting data...")
    train, test = train_test_split(data, test_size=0.4, stratify=data['species'], random_state=42)
    X_train = train[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]
    y_train = train.species
    X_test = test[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]
    y_test = test.species
    print("Data split complete.")

    print("Training Decision Tree model...")
    mod_dt = DecisionTreeClassifier(max_depth=3, random_state=1)
    mod_dt.fit(X_train, y_train)
    print("Model training complete.")

    print("Evaluating model...")
    prediction = mod_dt.predict(X_test)
    accuracy = metrics.accuracy_score(prediction, y_test)
    print(f'The accuracy of the Decision Tree is: {accuracy:.3f}')

    print(f"Saving metrics to {METRICS_FILE}...")
    with open(METRICS_FILE, "w") as f:
        f.write(f"Accuracy: {accuracy:.3f}\n")
    print("Metrics saved.")

    print(f"Saving model to {MODEL_PATH}...")
    joblib.dump(mod_dt, MODEL_PATH)
    print(f"Model saved successfully to {MODEL_PATH}")

    return accuracy

if __name__ == "__main__":
    print("Running train.py as a script...")
    train_and_evaluate()
    print("train.py script finished.")