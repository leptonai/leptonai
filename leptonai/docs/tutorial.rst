Tutorial
========

After installation, ``pip`` adds a new command ``lep`` to your environment. You can use this ``lep`` command line tool to create, run and manage AI model and application services both locally and on Lepton Inference Platform.

You can serve an existing model from Hugging Face with a single ``lep photon run`` command:


::

   $ lep photon run --name gpt2 --model hf:gpt2

   Photon "gpt2" does not exist
   Creating Photon: gpt2
   Photon gpt2 created
   * Serving Flask app 'gpt2'
   * Debug mode: off
   WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
   * Running on all addresses (0.0.0.0)
   * Running on http://127.0.0.1:8080
   * Running on http://10.128.0.5:8080
   Press CTRL+C to quit

Under the hood `lep` creates a photon (because it does not exist before) on the fly and launch an http server to run the corresponding photon. Once the photon service is up, you can send requests to the ``/run`` rest url with web requests tool, e.g.

Note that ``lep photon run``` supports remote deployment that instantiates the model on remote environments.

::

   # Use `curl` in a separate terminal tab
   $ curl http://localhost:8080/run -H 'content-type: application/json' -d '{"inputs": "a cat", "temperature": 0.7, "do_sample": true}'

   [{"generated_text":"a cat, but she likes to sleep under the covers.\n\n\"She's a nice girl, but she's not very good at sleeping,\" she said.\n\nThe girl was found wrapped in a blanket, wrapped in a blanket with tiny"}]


You can also use ``lep photon create`` to create the photon locally for a finer control, e.g.:


``$ lep photon create -n gpt2 -m hf:gpt2``

and use ``lep photon list`` and ``lep photon remove`` to manage photons:

::

   $ lep photon list

   +---------------------------------+
   |             Photons             |
   +------------+--------------------+
   |    Name    |        Model       |
   +============+====================+
   |    gpt2    |  hf:gpt2@e7da7f22  |
   +------------+--------------------+

::

   $ lep photon run --name gpt2

   * Serving Flask app 'gpt2'
   * Debug mode: off
   WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
   * Running on all addresses (0.0.0.0)
   * Running on http://127.0.0.1:8080
   * Running on http://10.128.0.5:8080
   Press CTRL+C to quit

::

   $ lep photon remove --name gpt2

   Photon "gpt2" removed
