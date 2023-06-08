# Start from golang v1.20 base image
FROM public.ecr.aws/docker/library/node:18.16.0-alpine as builder

# Copy everything from the current directory to the PWD(Present Working Directory) inside the container
COPY . /node/src/github.com/leptonai/lepton/web

# Set the Current Working Directory inside the container
WORKDIR /node/src/github.com/leptonai/lepton/web

# Build the Web app
RUN npm ci --force && npm run build

######## Start a new stage from scratch #######
FROM public.ecr.aws/nginx/nginx:stable-alpine-slim-amd64

# Copy the Pre-built binary file from the previous stage
COPY --from=builder /node/src/github.com/leptonai/lepton/web/dist /usr/share/nginx/html/
COPY --from=builder /node/src/github.com/leptonai/lepton/web/default.conf /etc/nginx/conf.d/
EXPOSE 80
