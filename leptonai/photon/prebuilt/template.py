from leptonai.photon import Photon


# TODO: change the name of the class "MyPhoton" to the name of your photon
class MyPhoton(Photon):
    """
    A template photon for you to get started. Replace this docstring with your
    photon's docstring.
    """

    # Add any dependencies that your photon requires. For example, if your photon
    # requires the `numpy` package, you can add it to the list below.
    requirement_dependency = [
        # "numpy",
    ]

    # Add any system dependencies that your photon requires. For example, if your
    # photon requires the `ffmpeg` package, you can add it to the list below.
    system_dependency = [
        # "ffmpeg",
    ]

    # Add a deployment template to remind users how to use the photon.
    # For example, if your photon has the following:
    #   - requires gpu.a10 to run
    #   - a required env variable called ENV_A, and the user needs to set the value.
    #   - an optional env variable called ENV_B with default value "DEFAULT_B"
    #   - a required secret called SECRET_A, and the user needs to choose the secret.
    # Then, the deployment template should look like:
    #     deployment_template: Dict = {
    #       "resource_shape": "gpu.a10",
    #       "env": {
    #         "ENV_A": ENV_VAR_REQUIRED,
    #         "ENV_B": "DEFAULT_B",
    #       },
    #       "secret": ["SECRET_A"],
    #     }
    deployment_template = {
        "resource_shape": None,
        "env": {},
        "secret": [],
    }

    # For more information about other configs of the photon, please refer to the
    # documentation at https://www.lepton.ai/docs/walkthrough/anatomy_of_a_photon

    def init(self):
        """
        The initialization function that will be called at the beginning of the
        photon's lifecycle. You can use this function to initialize any resources
        such as loading models, connecting to databases, etc.
        """
        pass

    # TODO: change the name of the function "run" to the name of your photon's
    # intended endpoint name. For example, if your photon is supposed to be
    # called with the endpoint `/hello`, you can change the name of the function
    # to `hello`. You can also add more endpoints by adding more functions decorated
    # with `@Photon.handler`.
    #
    # The input and output type hints are optional, although if you specify them,
    # the photon will be able to validate the input and output types of the endpoint.
    # Remember, since we are using Python, the argument and return types should all
    # be json serializable, such as int, float, string, and containers like list and
    # dict containing the serializable types.
    @Photon.handler
    def hello(self, name: str) -> str:
        """
        Replace this docstring with your endpoint's docstring.
        """
        return f"Hello, {name}!"


# The if statement below helps you to debug your photon locally. You can run
# the photon file directly with `python template.py` (or whatever you rename
# the file to) and it will start a local server.
if __name__ == "__main__":
    # TODO: change the name of the class "MyPhoton" to the name of your photon
    ph = MyPhoton()
    ph.launch(port=8080)
