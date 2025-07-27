import joblib
import pandas as pd
from fastapi import FastAPI, Request, HTTPException, Response, status
from pydantic import BaseModel
import logging
import json
import time

# --- OpenTelemetry Setup for Tracing ---
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

# Initialize the Tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)
# Configure the exporter to send traces to Google Cloud Trace
span_processor = BatchSpanProcessor(CloudTraceSpanExporter())
trace.get_tracer_provider().add_span_processor(span_processor)

# --- Structured Logging Setup ---
# Create a custom JSON formatter
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, self.datefmt),
            # Add trace context to logs
            "trace_id": trace.get_current_span().get_span_context().trace_id,
            "span_id": trace.get_current_span().get_span_context().span_id
        }
        return json.dumps(log_record)

# Configure the logger
logger = logging.getLogger("iris_classifier_logger")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)

# --- FastAPI Application ---
app = FastAPI()

# Input schema
class IrisInput(BaseModel):
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float

# Load the model
model = joblib.load("artifacts/model.joblib")

@app.get("/live_check", status_code=status.HTTP_200_OK, tags=["Health Checks"])
def liveness_probe():
    # A liveness probe just needs to return a 200 OK to say the app hasn't crashed.
    return {"status": "alive"}

@app.get("/ready_check", status_code=status.HTTP_200_OK, tags=["Health Checks"])
def readiness_probe():
    # A readiness probe can be more complex (e.g., check DB connection).
    # For us, we just check if the model is loaded. If this code is running, it is.
    if model:
        return {"status": "ready"}
    # If the model failed to load, this would not be reachable,
    # but as a fallback, we could return a 503 Service Unavailable.
    return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

@app.get("/")
def read_root():
    return {"message": "Iris Classifier API is running!"}

@app.post("/predict")
def predict_species(iris_input: IrisInput):
    # Start a new span for the prediction logic
    with tracer.start_as_current_span("iris_prediction_inference") as span:
        try:
            start_time = time.time()
            
            # Log the incoming request
            logger.info(f"Received prediction request: {iris_input.dict()}")
            span.set_attribute("request.body", iris_input.json())

            # Prediction logic
            input_data = pd.DataFrame([iris_input.dict()])
            prediction = model.predict(input_data)[0]
            probabilities = model.predict_proba(input_data)[0]
            class_names = model.classes_
            confidence_scores = {class_names[i]: float(probabilities[i]) for i in range(len(class_names))}
            
            latency = (time.time() - start_time) * 1000  # in ms
            span.set_attribute("prediction.latency_ms", latency)
            span.set_attribute("prediction.result", prediction)

            # Log the successful prediction
            logger.info(f"Prediction successful: {prediction}, Latency: {latency:.2f} ms")

            return {
                "predicted_species": prediction,
                "confidence_scores": confidence_scores
            }
        except Exception as e:
            # Log the error with trace context
            logger.error(f"Prediction failed with error: {e}", exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise HTTPException(status_code=500, detail="Internal Server Error")