FROM node:lts as builder

# Copy everything from the current directory to the PWD(Present Working Directory) inside the container
COPY web /node/src/github.com/leptonai/lepton/web

# Set the Current Working Directory inside the container
WORKDIR /node/src/github.com/leptonai/lepton/web

# Install pnpm@8
RUN npm install -g pnpm@8

# Skip install Cypress binary
ENV CYPRESS_INSTALL_BINARY=0

# Install dependencies
RUN pnpm install

# Build the dashboard app
RUN cd packages/dashboard && \
    pnpm build

######## Start a new stage from scratch #######
FROM amd64/nginx:latest

# Copy the Pre-built binary file from the previous stage
COPY --from=builder /node/src/github.com/leptonai/lepton/web/packages/dashboard/dist /usr/share/nginx/html/
COPY --from=builder /node/src/github.com/leptonai/lepton/web/default.conf /etc/nginx/conf.d/

WORKDIR /app

## add permissions for nginx user
RUN chown -R nginx:nginx /app && chmod -R 755 /app && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d
RUN touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

USER nginx
EXPOSE 8080
