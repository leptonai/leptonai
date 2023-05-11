## Get Started

1. [Install](https://redocly.com/docs/cli/installation/) redocly CLI
2. Read [OpenAPI Specification](https://swagger.io/specification/)
3. Edit json in [Editor](https://editor.swagger.io/), or find any json editor of your choice
4. Save api.json
5. Preview the result
```shell
  npx @redocly/cli preview-docs api.json  
```

> If you are not a fan with json, you may use tool like [json to yaml](https://onlineyamltools.com/convert-json-to-yaml) to preview yaml and do `redocly preview-docs api.yaml`, and vice versa

## Build

```shell
  npx @redocly/cli build-docs api.json
```


## Reference

- https://redocly.com/docs/
- https://swagger.io/specification/