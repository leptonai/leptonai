ARG CUDA_VERSION=11.7.0
ARG CUDNN_VERSION=8
ARG UBUNTU_VERSION=22.04

FROM nvcr.io/nvidia/cuda:${CUDA_VERSION}-cudnn${CUDNN_VERSION}-devel-ubuntu${UBUNTU_VERSION}

ARG TORCH_NIGHTLY=0

RUN if [ "$TORCH_NIGHTLY" = 0  -a "$CUDA_VERSION" != "11.7.0" ]; then \
    echo "CUDA version $CUDA_VERSION is not supported by PyTorch stable"; \
    exit 1; \
    fi

RUN if [ "$TORCH_NIGHTLY" = 1 -a "$CUDA_VERSION" != "12.1.0" ]; then \
    echo "CUDA version $CUDA_VERSION is not supported by PyTorch nightly"; \
    exit 1; \
    fi

RUN echo "TORCH_NIGHTLY=$TORCH_NIGHTLY"

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

COPY . /tmp/leptonai-sdk

ARG PYTHON_VERSION
ENV LEPTON_VIRTUAL_ENV=/opt/lepton/venv

RUN /tmp/leptonai-sdk/leptonai/photon/dockerfiles/install_base.sh
RUN sudo apt-get update && sudo apt-get install -y libgl1 ffmpeg

RUN /tmp/leptonai-sdk/leptonai/photon/dockerfiles/install_python.sh ${PYTHON_VERSION}
ENV PATH="$LEPTON_VIRTUAL_ENV/bin:$PATH"

RUN if [ "$TORCH_NIGHTLY" = 0 ]; then \
    pip install==2.0.1 torch torchvision torchaudio; \
    else \
    pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu121; \
    fi

RUN pip install uvicorn[standard] gradio!=3.31.0
RUN CT_CUBLAS=1 pip install ctransformers -U --no-binary --no-cache-dir ctransformers

RUN rm -rf /tmp/leptonai-sdk
