# Start from golang v1.20 base image
FROM golang:1.19 as builder

# Copy everything from the current directory to the PWD(Present Working Directory) inside the container
COPY . /go/src/github.com/leptonai/lepton/

# Set the Current Working Directory inside the container
WORKDIR /go/src/github.com/leptonai/lepton/server/

# Build the Go app
RUN GOARCH=amd64 GOOS=linux go build -a -ldflags \
    '-extldflags "-static"' -o lepton-server .

######## Start a new stage from scratch #######
FROM alpine:latest

# Copy the Pre-built binary file from the previous stage
COPY --from=builder /go/src/github.com/leptonai/lepton/server/lepton-server /app/
WORKDIR /app
EXPOSE 20863
CMD ["/app/lepton-server"]
