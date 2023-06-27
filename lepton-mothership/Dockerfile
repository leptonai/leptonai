# Use golang:1.19 as the base image for image build
FROM public.ecr.aws/docker/library/golang:1.19 as builder

RUN apt-get update && apt-get install -y curl unzip

# Build and install Terraform 1.4.6
RUN curl -LO https://releases.hashicorp.com/terraform/1.4.6/terraform_1.4.6_linux_amd64.zip && \
    unzip terraform_1.4.6_linux_amd64.zip -d /usr/local/bin/

# Install Helm
RUN curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz -o helm.tar.gz && \
    tar -zxvf helm.tar.gz && \
    mv linux-amd64/helm /usr/local/bin/helm

# Install kubectl
RUN curl -LO https://dl.k8s.io/release/v1.26.5/bin/linux/amd64/kubectl && \
    chmod +x kubectl && mv kubectl /usr/local/bin/

# Install jq
RUN curl -L https://github.com/jqlang/jq/releases/download/jq-1.6/jq-linux64 -o jq && \
    chmod +x jq && mv jq /usr/local/bin/

# Copy everything from the current directory to the PWD(Present Working Directory) inside the container
COPY . /go/src/github.com/leptonai/lepton/

# Set the Current Working Directory inside the container
WORKDIR /go/src/github.com/leptonai/lepton/lepton-mothership/

# Build
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -o mothership main.go

# Use aws cli as the base image
FROM public.ecr.aws/aws-cli/aws-cli:latest

# Install git
RUN yum update -y && yum install -y git

# Copy the built components from the builder stage
COPY --from=builder /usr/local/bin/terraform /usr/local/bin/terraform
COPY --from=builder /usr/local/bin/helm /usr/local/bin/helm
COPY --from=builder /usr/local/bin/kubectl /usr/local/bin/kubectl
COPY --from=builder /usr/local/bin/jq /usr/local/bin/jq

RUN mkdir /clusters
WORKDIR /clusters/
COPY --from=builder /go/src/github.com/leptonai/lepton/lepton-mothership/mothership /
EXPOSE 15213

ENTRYPOINT ["/mothership"]
