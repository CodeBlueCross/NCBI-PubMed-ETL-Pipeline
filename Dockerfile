# Use a lightweight Python base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies (pandas, google-cloud-storage, etc.)
# --no-cache-dir keeps the image small
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the code files into the container
COPY . .

# Set the default command to run when the container starts
ENTRYPOINT ["python", "run_pubmed_pipeline.py"]
