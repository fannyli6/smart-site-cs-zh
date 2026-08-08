# 多阶段构建：node 构建 -> nginx 托管静态资源并反代 /api 到后端
FROM node:18-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
# nginx:alpine 启动时会自动对 /etc/nginx/templates/*.template 做 envsubst
COPY --from=build /app/dist /usr/share/nginx/html
COPY default.conf.template /etc/nginx/templates/default.conf.template
# 后端地址：Sealos 部署时改为后端服务内部地址（如 http://ai-cs-backend:8000）
ENV BACKEND_URL=http://ai-cs-backend:8000
EXPOSE 80
