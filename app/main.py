import joblib
import pandas as pd
from fastapi import FastAPI, Request, HTTPException, Response, status
from pydantic import BaseModel
import logging
import json
import time
import os
import asyncio

# --- OpenTelemetry Setup for Tracing ---
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

# 1. Get the Project ID from the environment variable.
project_id = os.getenv("GCP_PROJECT_ID")

# 2. Initialize the Tracer Provider
trace.set_tracer_provider(TracerProvider())

# 3. Create the exporter, explicitly passing the project_id.
cloud_trace_exporter = CloudTraceSpanExporter(project_id=project_id)

# 4. Create a BatchSpanProcessor and add the exporter to it.
span_processor = BatchSpanProcessor(cloud_trace_exporter)

# 5. Add the processor to the tracer provider.
trace.get_tracer_provider().add_span_processor(span_processor)

# 6. Get a tracer for this service.
tracer = trace.get_tracer(__name__)


# --- Structured Logging Setup (remains the same) ---
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = { "severity": record.levelname, "message": record.getMessage(), "timestamp": self.formatTime(record, self.datefmt) }
        current_span = trace.get_current_span()
        if current_span:
            trace_id = current_span.get_span_context().trace_id
            if trace_id:
                log_record["trace_id"] = format(trace_id, "032x")
        return json.dumps(log_record)

logger = logging.getLogger("iris_classifier_logger")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)


# --- FastAPI Application ---
app = FastAPI()

class IrisInput(BaseModel):
    sepal_length: float; sepal_width: float; petal_length: float; petal_width: float

# Load the model (this is a synchronous operation, fine to do at startup)
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
async def predict_species(iris_input: IrisInput):
    with tracer.start_as_current_span("iris_prediction_inference") as span:
        try:
            start_time = time.time()
            
            logger.info(f"Received prediction request: {iris_input.dict()}")
            span.set_attribute("request.body", iris_input.json())

            # Model prediction is fast and CPU-bound, so running it directly is fine.
            # For a truly long-running model, you would use `asyncio.to_thread`
            input_data = pd.DataFrame([iris_input.dict()])
            prediction = model.predict(input_data)[0]
            probabilities = model.predict_proba(input_data)[0]
            class_names = model.classes_
            confidence_scores = {class_names[i]: float(probabilities[i]) for i in range(len(class_names))}
            
            # Simulate a small async delay, can be removed
            await asyncio.sleep(0.01)

            latency = (time.time() - start_time) * 1000
            span.set_attribute("prediction.latency_ms", latency)
            span.set_attribute("prediction.result", prediction)

            logger.info(f"Prediction successful: {prediction}, Latency: {latency:.2f} ms")

            return {"predicted_species": prediction, "confidence_scores": confidence_scores}
        except Exception as e:
            logger.error(f"Prediction failed with error: {e}", exc_info=True)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise HTTPException(status_code=500, detail="Internal Server Error")