FROM node:20-alpine

WORKDIR /app

# Copy package files and install dependencies
COPY frontend/package.json frontend/package-lock.json* /app/
RUN npm install

# Copy source code (will be overridden by volume mount in staging)
COPY frontend /app

EXPOSE 3000

# Keep the mounted staging node_modules volume in sync with package changes,
# then start Vite dev server binding to all interfaces on port 3000.
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0 --port 3000"]
