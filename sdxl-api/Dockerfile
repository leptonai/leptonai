FROM nvcr.io/nvidia/pytorch:23.08-py3

RUN git clone --recursive --branch flash_atten_v2 https://github.com/drisspg/pytorch.git /opt/torch
RUN pip install -r /opt/torch/requirements.txt
RUN pip install cmake ninja
RUN cd /opt/torch && python setup.py install
