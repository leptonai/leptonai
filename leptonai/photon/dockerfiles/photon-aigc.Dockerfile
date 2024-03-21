ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG WEBUI_REPO=https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
ARG WEBUI_SHA=v1.7.0

ARG SD_WEBUI_CONTROLNET_REPO=https://github.com/Mikubill/sd-webui-controlnet.git
ARG SD_WEBUI_CONTROLNET_SHA=679b627

ARG adetailer=https://github.com/Bing-su/adetailer.git
ARG ADDETAILER_SHA=8f01dfd

ARG CIVITAI_HELPER_REPO=https://github.com/butaixianran/Stable-Diffusion-Webui-Civitai-Helper.git
ARG CIVITAI_HELPER_SHA=b358572

RUN if [ ! -d /opt/lepton ]; then echo "/opt/lepton does not exist"; exit 1; fi

RUN git clone --recursive ${WEBUI_REPO} /opt/lepton/stable-diffusion-webui && \
    cd /opt/lepton/stable-diffusion-webui && \
    git checkout ${WEBUI_SHA} && \
    cd -

RUN mkdir -p /resources/extensions

RUN git clone --recursive ${SD_WEBUI_CONTROLNET_REPO} /opt/lepton/stable-diffusion-webui/extensions/sd-webui-controlnet && \
    cd /opt/lepton/stable-diffusion-webui/extensions/sd-webui-controlnet && \
    git checkout -B lepton ${SD_WEBUI_CONTROLNET_SHA} && \
    ln -sfT /opt/lepton/stable-diffusion-webui/extensions/sd-webui-controlnet /resources/extensions/sd-webui-controlnet && \
    cd -

RUN git clone --recursive ${adetailer} /opt/lepton/stable-diffusion-webui/extensions/adetailer && \
    cd /opt/lepton/stable-diffusion-webui/extensions/adetailer && \
    git checkout -B lepton ${ADDETAILER_SHA} && \
    ln -sfT /opt/lepton/stable-diffusion-webui/extensions/adetailer /resources/extensions/adetailer && \
    cd -

RUN git clone --recursive ${CIVITAI_HELPER_REPO} /opt/lepton/stable-diffusion-webui/extensions/Stable-Diffusion-Webui-Civitai-Helper && \
    cd /opt/lepton/stable-diffusion-webui/extensions/Stable-Diffusion-Webui-Civitai-Helper && \
    git checkout -B lepton ${CIVITAI_HELPER_SHA} && \
    ln -sfT /opt/lepton/stable-diffusion-webui/extensions/Stable-Diffusion-Webui-Civitai-Helper /resources/extensions/Stable-Diffusion-Webui-Civitai-Helper && \
    cd -

RUN pip install xformers==0.0.24 insightface==0.7.3
RUN cd /opt/lepton/stable-diffusion-webui && \
    venv_dir=- ./webui.sh -f --xformers --data-dir /resources --allow-code --skip-torch-cuda-test --exit && \
    cd -
