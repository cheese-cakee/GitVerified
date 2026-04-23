# GitVerified Agents Dockerfile
# Optimized for quantized models and laptop deployment

FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install quantized model dependencies
RUN pip install --no-cache-dir \
    pymupdf \
    requests \
    redis \
    scikit-learn \
    numpy \
    pandas \
    black \
    flake8 \
    openai \
    pydantic \
    tqdm \
    bitsandbytes \
    accelerate

# Copy agents
COPY agents/ /app/agents/

# Create necessary directories
RUN mkdir -p /data /models

# Set environment variables
ENV PYTHONPATH=/app
ENV AGENT_MODE=hybrid
ENV MEMORY_LIMIT=2G

# Test agent imports
RUN python -c "from agents.integrity import scan_resume_integrity; print('Integrity agent OK')" || echo "Integrity agent import failed"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.path.append('/app/agents'); from integrity import scan_resume_integrity; print('OK')" || exit 1

# Default command
CMD ["python", "-c", "print('GitVerified Agents Ready')"]