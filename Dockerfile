# Stage 1: Build stage with development dependencies
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies if any (e.g. for compiling some packages)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc

COPY requirements.txt .
# Using pip wheel to pre-compile dependencies
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Production stage
FROM python:3.10-slim

WORKDIR /app

# Create a non-root user for better security
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser

# Copy built wheels from the builder stage
COPY --from=builder /app/wheels /wheels

# Copy requirements.txt to install any remaining packages or ensure versions
COPY requirements.txt .

# Install runtime dependencies from wheels first, then from requirements.txt
# This ensures that C extensions are compatible.
# --no-build-isolation can be important if some packages have pyproject.toml but are not meant to be built in isolation by pip
RUN pip install --no-cache /wheels/* && \
    pip install -r requirements.txt --no-build-isolation && \
    rm -rf /wheels

# Copy application code into the container
# Ensure .dockerignore is properly set up to exclude venv, .git, etc.
COPY . .

# Download spaCy model during build time.
# This increases image size but ensures the model is present at runtime.
# Ensure the user running this has internet access to download the model.
RUN python -m spacy download fr_core_news_sm

# Change ownership of the /app directory to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose the port the application will run on
EXPOSE 8000

# Set environment variables for Uvicorn host and port
ENV HOST 0.0.0.0
ENV PORT 8000

# Command to run the application using Uvicorn
# Note: --reload is for development and should be removed or disabled in production.
# CMD ["uvicorn", "sass_legal.api.main:app", "--host", "$HOST", "--port", "$PORT", "--reload"]
CMD ["uvicorn", "sass_legal.api.main:app", "--host", "$HOST", "--port", "$PORT"]
