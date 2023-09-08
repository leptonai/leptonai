#include <torch/csrc/cuda/CUDAPluggableAllocator.h>

#include <cuda_runtime_api.h>
#include <mutex>
#include <sys/types.h>
#include <unordered_map>

namespace tum {

struct Metadata {
  ssize_t size;
  int device;
  cudaStream_t stream;

  Metadata(ssize_t size, int device, cudaStream_t stream)
      : size(size), device(device), stream(stream) {}
};

class TumAllocator {
  std::mutex metadata_mutex_;

public:
  std::unordered_map<void *, Metadata> metadata;
  TumAllocator() : metadata_mutex_(), metadata() {}
  void *malloc(ssize_t size, int device, cudaStream_t stream);
  void free(void *ptr, ssize_t size, int device, cudaStream_t stream);
  void prefetch();
};

TumAllocator &get_allocator();

bool is_current_allocator_initialized();
} // namespace tum
