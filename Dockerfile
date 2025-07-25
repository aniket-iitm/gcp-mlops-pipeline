# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed dependencies specified in requirements.txt
# --no-cache-dir reduces image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and the trained model artifacts
# Note: We copy the entire 'Week 4' content from the build context
# into the /app directory of the container.
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the app using uvicorn
# This will run when the container launches.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]