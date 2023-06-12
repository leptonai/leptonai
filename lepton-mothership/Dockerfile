# Use golang:1.19 as the base image for image build
FROM public.ecr.aws/docker/library/golang:1.19 as builder

RUN apt-get update && apt-get install -y curl unzip git

# Build and install Terraform 1.4.6
RUN curl -LO https://releases.hashicorp.com/terraform/1.4.6/terraform_1.4.6_linux_amd64.zip && \
    unzip terraform_1.4.6_linux_amd64.zip -d /usr/local/bin/

# Install Helm
RUN curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz -o helm.tar.gz && \
    tar -zxvf helm.tar.gz && \
    mv linux-amd64/helm /usr/local/bin/helm

# Install EKS CLI (eksctl)
RUN curl -L https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_Linux_amd64.tar.gz | tar xz -C /tmp && \
    mv /tmp/eksctl /usr/local/bin

# Copy everything from the current directory to the PWD(Present Working Directory) inside the container
COPY . /go/src/github.com/leptonai/lepton/

# Set the Current Working Directory inside the container
WORKDIR /go/src/github.com/leptonai/lepton/lepton-mothership/

# Build
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -o mothership main.go

# Use aws cli as the base image
FROM public.ecr.aws/aws-cli/aws-cli:latest

# Copy the built components from the builder stage
COPY --from=builder /usr/local/bin/terraform /usr/local/bin/terraform
COPY --from=builder /usr/bin/git /usr/bin/git
COPY --from=builder /usr/local/bin/helm /usr/local/bin/helm
COPY --from=builder /usr/local/bin/eksctl /usr/local/bin/eksctl

WORKDIR /
COPY --from=builder /go/src/github.com/leptonai/lepton/lepton-mothership/mothership .
USER 65532:65532
EXPOSE 15213

ENTRYPOINT ["/mothership"]
