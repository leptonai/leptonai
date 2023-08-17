# Installation

```bash
cd ${HOME}/lepton
go build -o /tmp/mo ./mothership/cmd/mothership
/tmp/mo -h
cp /tmp/mo ${GOPATH}/bin/mo
```

## List clusters using `machine` CLI

```bash
cd ${HOME}/lepton
go build -o /tmp/ma ./machine
/tmp/ma -h
cp /tmp/ma ${GOPATH}/bin/ma
```

```bash
# to check whoami
ma a w

ma a s l
ma a s g mothership_url
ma a s g mothership_api_token

mo c l \
--mothership-url "$(ma a s g mothership_url)" \
--token "$(ma a s g mothership_api_token)"
```
