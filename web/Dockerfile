# SCRUM-62: container image for the Vite + React dev server.

FROM node:22-alpine

WORKDIR /app

# Dependencies on their own cached layer, same idea as the API.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite only listens on localhost by default. --host makes it listen on all
# interfaces so your browser can reach it through the container's port.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]