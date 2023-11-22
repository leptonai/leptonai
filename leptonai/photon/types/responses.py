from fastapi.responses import StreamingResponse


class PNGResponse(StreamingResponse):
    media_type = "image/png"


class WAVResponse(StreamingResponse):
    media_type = "audio/wav"


class JPEGResponse(StreamingResponse):
    media_type = "image/jpeg"
