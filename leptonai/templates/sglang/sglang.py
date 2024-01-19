import os
import sys
import time
from typing import List, Optional, Union

from leptonai.photon import Photon, HTTPException
from leptonai.photon.types import File

from loguru import logger


class SGLang(Photon):
    """
    A photon wrapper of the sgl-project's SRT server.
    """

    requirement_dependency = [
        "sglang[all]==0.1.5",
    ]

    deployment_template = {
        "resource_shape": "gpu.a10",
        "env": {
            "WHISPER_MODEL": "large-v3",
            # maximum audio length that the api allows. In default, we will use
            # 10 minutes. If you are deploying things on your own, you can change
            # it to be longer.
            "MAX_LENGTH_IN_SECONDS": "600",
        },
        "secret": [
            "HUGGING_FACE_HUB_TOKEN",
        ],
    }

    # If one is doing a lot of alignments and diarizations, it is possible that
    # the gpu is underutilized. In this case, one can increase the concurrency
    # to better utilize the gpu.
    handler_max_concurrency = 8

    def init(self):
        """
        Initializes the sglang server. This is a transcribed version of the
        sglang.srt.server.launch_server function, with some modification to
        cope with 
        """
        from sglang.srt import server
        from sglang.srt.server_args import ServerArgs

        server_args = ServerArgs()

        # Allocate ports
        can_use_ports = server.alloc_usable_network_port(
            num=4 + server_args.tp_size, used_list=(server_args.port,)
        )
        port_args = PortArgs(
            tokenizer_port=can_use_ports[0],
            router_port=can_use_ports[1],
            detokenizer_port=can_use_ports[2],
            nccl_port=can_use_ports[3],
            model_rpc_ports=can_use_ports[4:],
        )

        # Load chat template if needed
        if server_args.chat_template is not None:
            if not chat_template_exists(server_args.chat_template):
                if not os.path.exists(server_args.chat_template):
                    raise RuntimeError(
                        f"Chat template {server_args.chat_template} is not a built-in template name "
                        "or a valid chat template file path."
                    )
                with open(server_args.chat_template, "r") as filep:
                    template = json.load(filep)
                    try:
                        sep_style = SeparatorStyle[template["sep_style"]]
                    except KeyError:
                        raise ValueError(
                            f"Unknown separator style: {template['sep_style']}"
                        ) from None
                    register_conv_template(
                        Conversation(
                            name=template["name"],
                            system_template=template["system"] + "\n{system_message}",
                            system_message=template.get("system_message", ""),
                            roles=(template["user"], template["assistant"]),
                            sep_style=sep_style,
                            sep=template.get("sep", "\n"),
                            stop_str=template["stop_str"],
                        ),
                        override=True,
                    )
                server.chat_template_name = template["name"]
            else:
                server.chat_template_name = server_args.chat_template

        # Launch processes
        server.tokenizer_manager = TokenizerManager(server_args, port_args)
        pipe_router_reader, pipe_router_writer = mp.Pipe(duplex=False)
        pipe_detoken_reader, pipe_detoken_writer = mp.Pipe(duplex=False)

        proc_router = mp.Process(
            target=start_router_process,
            args=(
                server_args,
                port_args,
                pipe_router_writer,
            ),
        )
        proc_router.start()
        proc_detoken = mp.Process(
            target=start_detokenizer_process,
            args=(
                server_args,
                port_args,
                pipe_detoken_writer,
            ),
        )
        proc_detoken.start()

        # Wait for the model to finish loading
        router_init_state = pipe_router_reader.recv()
        detoken_init_state = pipe_detoken_reader.recv()

        if router_init_state != "init ok" or detoken_init_state != "init ok":
            proc_router.kill()
            proc_detoken.kill()
            print("router init state:", router_init_state)
            print("detoken init state:", detoken_init_state)
            sys.exit(1)

        assert proc_router.is_alive() and proc_detoken.is_alive()

        def launch_server():
            # Launch api server
            uvicorn.run(
                app,
                host=server_args.host,
                port=server_args.port,
                log_level=server_args.log_level,
                timeout_keep_alive=5,
                loop="uvloop",
            )

        t = threading.Thread(target=launch_server)
        t.start()



    @Photon.handler(mount=True)
    def api(self):
        from sglang.srt import server

        return server.app

if __name__ == "__main__":
    p = SGLang()
    p.launch()
