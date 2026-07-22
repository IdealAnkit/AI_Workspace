# ==============================================================================
# Frontend Dockerfile — Development
# ==============================================================================

FROM node:22-alpine

# Set working directory
WORKDIR /app

# Install dependencies first (better Docker layer caching)
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Start Vite dev server — binding to 0.0.0.0 is required for Docker
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
