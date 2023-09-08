#include <cuda_runtime_api.h>
#include <sys/types.h>
#include <tum/allocator.h>

extern "C" {
void *tum_malloc(ssize_t size, int device, cudaStream_t stream) {
  return tum::get_allocator().malloc(size, device, stream);
}

void tum_free(void *ptr, ssize_t size, int device, cudaStream_t stream) {
  return tum::get_allocator().free(ptr, size, device, stream);
}
}
