ARG BASE_IMAGE
FROM ${BASE_IMAGE}

RUN if [ ! -d /opt/lepton ]; then echo "/opt/lepton does not exist"; exit 1; fi

ARG WEBUI_REPO=https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
ARG WEBUI_SHA=v1.7.0

ARG WEBUI_CONTROLNET_REPO=https://github.com/Mikubill/sd-webui-controlnet.git
ARG WEBUI_CONTROLNET_SHA=679b627

ARG WEBUI_ADETAILER_REPO=https://github.com/Bing-su/adetailer.git
ARG WEBUI_ADETAILER_SHA=8f01dfd

ARG WEBUI_CIVITAI_HELPER_REPO=https://github.com/butaixianran/Stable-Diffusion-Webui-Civitai-Helper.git
ARG WEBUI_CIVITAI_HELPER_SHA=b358572

RUN git clone --recursive ${WEBUI_REPO} /opt/lepton/stable-diffusion-webui && \
    cd /opt/lepton/stable-diffusion-webui && \
    git checkout ${WEBUI_SHA} && \
    cd -

RUN mkdir -p /resources/extensions

RUN git clone --recursive ${WEBUI_CONTROLNET_REPO} /opt/lepton/stable-diffusion-webui/extensions/sd-webui-controlnet && \
    cd /opt/lepton/stable-diffusion-webui/extensions/sd-webui-controlnet && \
    git checkout -B lepton ${WEBUI_CONTROLNET_SHA} && \
    ln -sfT /opt/lepton/stable-diffusion-webui/extensions/sd-webui-controlnet /resources/extensions/sd-webui-controlnet && \
    cd -

RUN git clone --recursive ${WEBUI_ADETAILER_REPO} /opt/lepton/stable-diffusion-webui/extensions/adetailer && \
    cd /opt/lepton/stable-diffusion-webui/extensions/adetailer && \
    git checkout -B lepton ${WEBUI_ADETAILER_SHA} && \
    ln -sfT /opt/lepton/stable-diffusion-webui/extensions/adetailer /resources/extensions/adetailer && \
    cd -

RUN git clone --recursive ${WEBUI_CIVITAI_HELPER_REPO} /opt/lepton/stable-diffusion-webui/extensions/Stable-Diffusion-Webui-Civitai-Helper && \
    cd /opt/lepton/stable-diffusion-webui/extensions/Stable-Diffusion-Webui-Civitai-Helper && \
    git checkout -B lepton ${WEBUI_CIVITAI_HELPER_SHA} && \
    ln -sfT /opt/lepton/stable-diffusion-webui/extensions/Stable-Diffusion-Webui-Civitai-Helper /resources/extensions/Stable-Diffusion-Webui-Civitai-Helper && \
    cd -

RUN pip install xformers==0.0.24 insightface==0.7.3
RUN cd /opt/lepton/stable-diffusion-webui && \
    venv_dir=- ./webui.sh -f --xformers --data-dir /resources --allow-code --skip-torch-cuda-test --exit && \
    cd -

ARG COMFYUI_REPO=https://github.com/comfyanonymous/ComfyUI.git
ARG COMFYUI_SHA=bf3e334

ARG COMFYUI_MANAGER_REPO=https://github.com/ltdrdata/ComfyUI-Manager.git
ARG COMFYUI_MANAGER_SHA=ba78eaa

RUN git clone --recursive ${COMFYUI_REPO} /opt/lepton/ComfyUI && \
    cd /opt/lepton/ComfyUI && \
    git checkout ${COMFYUI_SHA} && \
    cd -

RUN cd /opt/lepton/ComfyUI && \
    pip install -r requirements.txt

RUN git clone --recursive ${COMFYUI_MANAGER_REPO} /opt/lepton/ComfyUI/custom_nodes/ComfyUI-Manager && \
    cd /opt/lepton/ComfyUI/custom_nodes/ComfyUI-Manager && \
    git checkout ${COMFYUI_MANAGER_SHA} && \
    pip install -r requirements.txt && \
    cd -
