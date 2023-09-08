#include <c10/cuda/CUDACachingAllocator.h>
#include <c10/cuda/CUDAException.h>
#include <iostream>
#include <tum/allocator.h>

namespace tum {
void *TumAllocator::malloc(ssize_t size, int device, cudaStream_t stream) {
  if (size == 0) {
    return nullptr;
  }
  void *ptr;
  C10_CUDA_CHECK(cudaMallocManaged(&ptr, size));
  if (stream != nullptr) {
    C10_CUDA_CHECK(cudaStreamAttachMemAsync(stream, ptr));
  }
  {
    std::lock_guard<std::mutex> lock(metadata_mutex_);
    metadata.emplace(ptr, Metadata(size, device, stream));
  }
  return ptr;
}

void TumAllocator::free(void *ptr, ssize_t size, int device,
                        cudaStream_t stream) {
  if (ptr == nullptr) {
    return;
  }
  {
    std::lock_guard<std::mutex> lock(metadata_mutex_);
    TORCH_CHECK(metadata.count(ptr),
                "Memory was not allocated by TUM allocator: ", ptr);
    metadata.erase(ptr);
  }
  cudaFree(ptr);
}

void TumAllocator::prefetch() {
  std::lock_guard<std::mutex> lock(metadata_mutex_);
  for (auto &entry : metadata) {
    auto *ptr = entry.first;
    auto &val = entry.second;
    C10_CUDA_CHECK(cudaMemPrefetchAsync(ptr, val.size, val.device, val.stream));
  }
}

bool is_current_allocator_initialized() {
  const auto &allocator = c10::cuda::CUDACachingAllocator::get();
  // Is it possible for the allocator to be null here?
  if (!allocator) {
    return false;
  }
  return allocator->initialized();
}

TumAllocator &get_allocator() {
  static TumAllocator allocator;
  return allocator;
}
} // namespace tum
