# Build stage
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Pass service URLs at build time: docker build --build-arg VITE_RAG_URL=... .
ARG VITE_API_URL=""
ARG VITE_RECOMMEND_URL=""
ARG VITE_RAG_URL=""
ENV VITE_API_URL=$VITE_API_URL VITE_RECOMMEND_URL=$VITE_RECOMMEND_URL VITE_RAG_URL=$VITE_RAG_URL
RUN npm run build

# Serve stage
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
