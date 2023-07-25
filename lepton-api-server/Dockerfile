# Start from golang v1.20 base image
FROM public.ecr.aws/docker/library/golang:1.19 as builder

# Copy everything from the current directory to the PWD(Present Working Directory) inside the container
COPY . /go/src/github.com/leptonai/lepton/

# Set the Current Working Directory inside the container
WORKDIR /go/src/github.com/leptonai/lepton/lepton-api-server/

# Build the Go app
ARG GIT_COMMIT=HEAD
RUN BUILD_TIME=$(date -u +"%Y-%m-%d_%H-%M-%S") && CGO_ENABLED=0 GOARCH=amd64 GOOS=linux go build -a -ldflags \
    "-X github.com/leptonai/lepton/go-pkg/version.GitCommit=${GIT_COMMIT} \
    -X github.com/leptonai/lepton/go-pkg/version.BuildTime=${BUILD_TIME} \
    -extldflags \"-static\"" \
    -o lepton-api-server .

######## Start a new stage from scratch #######
FROM public.ecr.aws/docker/library/alpine:latest

# Copy the Pre-built binary file from the previous stage
COPY --from=builder /go/src/github.com/leptonai/lepton/lepton-api-server/lepton-api-server /app/
WORKDIR /app
EXPOSE 20863
USER 65532:65532
CMD ["/app/lepton-api-server"]
