FROM node:20-alpine

WORKDIR /app

# Copy package files and install dependencies
COPY frontend/package.json frontend/package-lock.json* /app/
RUN npm install

# Copy source code to persist it inside the production container (no volume mount)
COPY frontend /app

EXPOSE 3000

# Start Vite dev server on port 3000 for the transitionary production setup
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
