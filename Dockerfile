# Use an official AWS Lambda Python 3.12 base image
FROM public.ecr.aws/lambda/python:3.12

# Set the working directory in the container
WORKDIR /var/task

# --- Install Python Dependencies ---
# Copy only the requirements file first to leverage Docker's layer caching.
# This layer will only be rebuilt if the requirements change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copy Application Code ---
# Copy the main server files and the entire 'src' directory
COPY pipeline_server.py .
COPY lambda_function.py .
COPY config.yaml .
COPY src/ ./src/

# Set the command that AWS Lambda will run when the container starts.
# This points to the lambda_handler function in the lambda_function.py file.
CMD [ "lambda_function.lambda_handler" ]