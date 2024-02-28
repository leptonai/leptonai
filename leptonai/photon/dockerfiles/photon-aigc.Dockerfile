ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG WEBUI_REPO=https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
ARG WEBUI_SHA=v1.7.0

ARG SD_WEBUI_CONTROLNET_REPO=https://github.com/Mikubill/sd-webui-controlnet.git
ARG SD_WEBUI_CONTROLNET_SHA=679b627

ARG adetailer=https://github.com/Bing-su/adetailer.git
ARG ADDETAILER_SHA=8f01dfd

RUN if [ ! -d /opt/lepton ]; then echo "/opt/lepton does not exist"; exit 1; fi

RUN git clone --recursive ${WEBUI_REPO} /opt/lepton/stable-diffusion-webui && \
    cd /opt/lepton/stable-diffusion-webui && \
    git checkout ${WEBUI_SHA} && \
    cd -

RUN mkdir -p /resources/extensions

RUN git clone --recursive ${SD_WEBUI_CONTROLNET_REPO} /resources/extensions/sd-webui-controlnet && \
    cd /resources/extensions/sd-webui-controlnet && \
    git checkout -B lepton ${SD_WEBUI_CONTROLNET_SHA} && \
    cd -

RUN git clone --recursive ${adetailer} /resources/extensions/adetailer && \
    cd /resources/extensions/adetailer && \
    git checkout -B lepton ${ADDETAILER_SHA} && \
    cd -

RUN pip install xformers
RUN cd /opt/lepton/stable-diffusion-webui && \
    venv_dir=- ./webui.sh -f --xformers --data-dir /resources --allow-code --skip-torch-cuda-test --exit && \
    cd -
