# Use golang:1.19 as the base image for image build
FROM public.ecr.aws/docker/library/golang:1.19 as builder

# Copy everything from the current directory to the PWD(Present Working Directory) inside the container
COPY . /go/src/github.com/leptonai/lepton/

# Set the Current Working Directory inside the container
WORKDIR /go/src/github.com/leptonai/lepton/lepton-mothership/cmd/mothership

# Build
ARG GIT_COMMIT=HEAD
RUN BUILD_TIME=$(date -u +"%Y-%m-%d_%H-%M-%S") && CGO_ENABLED=0 GOARCH=amd64 GOOS=linux go build -a -ldflags \
    "-X github.com/leptonai/lepton/go-pkg/version.GitCommit=${GIT_COMMIT} \
    -X github.com/leptonai/lepton/go-pkg/version.BuildTime=${BUILD_TIME} \
    -extldflags \"-static\"" \
    -o mothershipctl .

FROM public.ecr.aws/aws-cli/aws-cli:latest
COPY --from=builder /go/src/github.com/leptonai/lepton/lepton-mothership/cmd/mothership/mothershipctl /
ENTRYPOINT ["/mothershipctl"]
