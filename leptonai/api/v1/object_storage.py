from leptonai.api.v1.api_resource import APIResourse


class ObjectStorageAPI(APIResourse):

    def create_object_url_for_get(self, object_key, return_url=False):
        response = self._get(f"/object_storage/private_presigned/{object_key}", allow_redirects=not return_url, stream=True)
        return response
