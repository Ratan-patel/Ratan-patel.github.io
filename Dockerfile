# Self-hosted production image (nginx). Works on Railway, Fly.io, Render, any VPS.
FROM nginx:1.27-alpine

# Copy site
COPY . /usr/share/nginx/html

# Remove build/dev artifacts
RUN rm -rf /usr/share/nginx/html/node_modules \
           /usr/share/nginx/html/package.json \
           /usr/share/nginx/html/package-lock.json \
           /usr/share/nginx/html/.git \
           /usr/share/nginx/html/Dockerfile

# Custom nginx config for security headers + SPA 404 fallback
RUN printf 'server {\n\
  listen 80;\n\
  server_name _;\n\
  root /usr/share/nginx/html;\n\
  index index.html;\n\
\n\
  # Security headers\n\
  add_header X-Content-Type-Options nosniff always;\n\
  add_header X-Frame-Options SAMEORIGIN always;\n\
  add_header X-XSS-Protection "1; mode=block" always;\n\
  add_header Referrer-Policy strict-origin-when-cross-origin always;\n\
  add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;\n\
  add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;\n\
\n\
  # Long cache for static assets\n\
  location ~* \\.(js|css|png|jpg|jpeg|gif|webp|svg|woff2?|ttf)$ {\n\
    expires 1y;\n\
    add_header Cache-Control "public, immutable";\n\
  }\n\
\n\
  # 404 fallback\n\
  error_page 404 /404.html;\n\
  location = /404.html { internal; }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
