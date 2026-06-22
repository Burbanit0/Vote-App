# Stage 1: Build the React app
FROM node:20 AS build

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm cache clean --force
RUN npm install

# Copy the rest of the application
COPY . .

# Build the application
RUN npm run build

# Stage 2: Serve the app with a NON-ROOT Nginx (hardening). The unprivileged
# image runs as the 'nginx' user and listens on 8080 (a >1024 port a non-root
# process may bind). Map it at run time, e.g. `docker run -p 8080:8080 …`.
FROM nginxinc/nginx-unprivileged:alpine

USER root
# SPA routing config on the unprivileged port (single-quoted so $uri stays literal).
RUN printf 'server {\n    listen 8080;\n    location / {\n        root /usr/share/nginx/html;\n        index index.html;\n        try_files $uri $uri/ /index.html;\n    }\n}\n' > /etc/nginx/conf.d/default.conf

# Copy the built app
COPY --from=build /app/build /usr/share/nginx/html

USER nginx
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
