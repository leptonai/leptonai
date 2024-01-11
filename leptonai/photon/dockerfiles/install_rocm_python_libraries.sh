# building amd's common libraries that are needed for the rocm python libraries,
# and are otherwise timeconsuming to build.

# flash-attention
pushd /tmp
git clone --recursive https://github.com/ROCmSoftwarePlatform/flash-attention.git
cd flash-attention
git checkout 68aac13  # Pin to end of Dec 2023.
export GPU_ARCHS="gfx90a"
export PYTHON_SITE_PACKAGES=$(python -c 'import site; print(site.getsitepackages()[0])')
pip install .
cd ..
rm -rf /tmp/flash-attention

# vllm
git clone https://github.com/vllm-project/vllm.git
cd vllm
git checkout v0.2.7
# xformers
pip install xformers==0.0.23 --no-deps
bash patch_xformers.rocm.sh

pip install -U -r requirements-rocm.txt
python setup.py install
cd ..
rm -rf /tmp/vllm

popd
