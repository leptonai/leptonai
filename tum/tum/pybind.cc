#include <torch/extension.h>
#include <tum/allocator.h>

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
  m.def("is_current_allocator_initialized",
        &tum::is_current_allocator_initialized,
        "Check if current allocator is initialized");
  m.def(
      "prefetch", [] { tum::get_allocator().prefetch(); },
      "Prefetch all (live) allocated memory to the GPU");
  py::class_<tum::Metadata>(m, "Metadata")
      .def_readonly("size", &tum::Metadata::size)
      .def_readonly("device", &tum::Metadata::device)
      .def_property_readonly("stream", [](const tum::Metadata &self) {
        return reinterpret_cast<int64_t>(self.stream);
      });
  m.def("metadata", []() { return tum::get_allocator().metadata; });
}
