import tempfile
import os
from leptonai.photon import Photon
from fastapi import UploadFile, File

class Transcriber(Photon):
    # The init method implements any custom initialization logic we need.
    requirement_dependency = ["Cython", "packaging", "nemo_toolkit[all]", "huggingface-hub==0.23.2", "numpy==1.26.3"]
    system_dependency = ["libsndfile1", "ffmpeg"]

    def init(self):
        from nemo.collections.asr.models import EncDecMultiTaskModel
        self.asr_model = EncDecMultiTaskModel.from_pretrained('nvidia/canary-1b')

    # When no name is specified, the handler name is the method name.
    @Photon.handler("/transcribe_audio/", method="POST", use_raw_args=True)
    async def transcribe_audio(self, file: UploadFile = File(...)):
        # Save the uploaded file to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        
        # Use the temporary file path for transcription
        try:
            transcript = self.asr_model.transcribe(
                paths2audio_files=[tmp_path],  # Pass the path to the temporary file
                batch_size=1
            )
        finally:
            # Clean up the temporary file after transcription
            os.remove(tmp_path)

        # Return the transcript as a JSON response
        return {"transcript": transcript}