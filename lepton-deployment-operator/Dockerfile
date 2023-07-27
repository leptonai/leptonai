ARG REPO=public.ecr.aws
# Build the manager binary
FROM ${REPO}/docker/library/golang:1.19 as builder

# Copy everything from the current directory to the PWD(Present Working Directory) inside the container
COPY . /go/src/github.com/leptonai/lepton/

# Set the Current Working Directory inside the container
WORKDIR /go/src/github.com/leptonai/lepton/lepton-deployment-operator/

# Build
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -o manager cmd/main.go

# Use distroless as minimal base image to package the manager binary
# Refer to https://github.com/GoogleContainerTools/distroless for more details
FROM ${REPO}/docker/library/alpine:latest

WORKDIR /
COPY --from=builder /go/src/github.com/leptonai/lepton/lepton-deployment-operator/manager .
USER 65532:65532

ENTRYPOINT ["/manager"]
