# Lepton CLI Usage Examples

## Table of Contents
- [Ingress Canary Deployments](#ingress-canary-deployments)
- [IP Whitelist](#ip-whitelist-usage-examples)

---

## Ingress Canary Deployments

The Lepton CLI supports canary-style deployments through ingress endpoint management. This allows you to gradually roll out new versions by controlling traffic distribution between deployments.

### Quick Start: Canary Deployment

```bash
# 1. Deploy new version (canary)
lep deployment create -n canary-deployment --photon-id my-photon-v2

# 2. Add canary to existing ingress with 10% traffic
lep ingress add-endpoint -n api.example.com -d canary-deployment -w 10

# 3. Gradually increase traffic to canary
lep ingress update-endpoint -n api.example.com -d canary-deployment -w 50

# 4. Complete rollout - route all traffic to canary
lep ingress set-endpoints -n api.example.com -e canary-deployment:100
```

### Available Ingress Commands

- `lep ingress add-endpoint` - Add a deployment to an ingress with traffic weight
- `lep ingress update-endpoint` - Update traffic weight for a deployment
- `lep ingress set-endpoints` - Set all endpoints and weights at once
- `lep ingress remove-endpoint` - Remove a deployment from an ingress
- `lep ingress list` - List all ingresses
- `lep ingress get` - View details of a specific ingress

For a complete guide with examples, see [docs/ingress_canary_deployment_guide.md](docs/ingress_canary_deployment_guide.md).

---

# IP Whitelist Usage Examples

## Clean Separation of Concerns

The IP whitelist functionality now correctly follows this clean design:
- **IP Access Control**: `--public` vs `--ip-whitelist` (network/ingress level)
- **Authentication**: `--tokens` (application level, completely independent)

## Key Design Principles

1. **`--public`**: Endpoint accessible from any IP address (equivalent to `--ip-whitelist` with empty array)
2. **`--ip-whitelist`**: Endpoint only accessible from specified IP addresses/CIDR ranges
3. **`--tokens`**: Authentication tokens required (completely independent of IP access control)
4. **Mutual Exclusivity**: `--public` and `--ip-whitelist` cannot be used together

## Valid Usage Examples

### 1. Public Endpoint (Accessible from any IP, no authentication tokens)
```bash
lep endpoint create \
  --name public-endpoint \
  --resource-shape cpu.tiny \
  --container-image python:3.9-slim \
  --container-port 8080 \
  --container-command 'python3 -m http.server 8080' \
  --public
```

### 2. Public Endpoint with Authentication Tokens
```bash
lep endpoint create \
  --name public-endpoint-with-auth \
  --resource-shape cpu.tiny \
  --container-image python:3.9-slim \
  --container-port 8080 \
  --container-command 'python3 -m http.server 8080' \
  --public \
  --tokens my-token-1 \
  --tokens my-token-2
```

### 3. IP-Whitelisted Endpoint (Default: workspace token required)
```bash
lep endpoint create \
  --name ip-restricted-endpoint \
  --resource-shape cpu.tiny \
  --container-image python:3.9-slim \
  --container-port 8080 \
  --container-command 'python3 -m http.server 8080' \
  --ip-whitelist 128.77.86.0/24 \
  --ip-whitelist 192.168.1.0/24
```

### 4. IP-Whitelisted Endpoint with Comma-Separated Values
```bash
lep endpoint create \
  --name ip-restricted-endpoint-comma \
  --resource-shape cpu.tiny \
  --container-image python:3.9-slim \
  --container-port 8080 \
  --container-command 'python3 -m http.server 8080' \
  --ip-whitelist "128.77.86.0/24,192.168.1.0/24,10.0.0.0/8"
```

### 5. IP-Whitelisted Endpoint with Authentication Tokens
```bash
lep endpoint create \
  --name ip-restricted-endpoint-with-auth \
  --resource-shape cpu.tiny \
  --container-image python:3.9-slim \
  --container-port 8080 \
  --container-command 'python3 -m http.server 8080' \
  --ip-whitelist "128.77.86.0/24,10.0.0.0/8" \
  --tokens my-token-1 \
  --tokens my-token-2
```

### 6. Private Endpoint (Default: workspace token required, no IP restrictions)
```bash
lep endpoint create \
  --name private-endpoint \
  --resource-shape cpu.tiny \
  --container-image python:3.9-slim \
  --container-port 8080 \
  --container-command 'python3 -m http.server 8080'
  # No --public or --ip-whitelist specified
```

### 7. Private Endpoint with Additional Authentication Tokens
```bash
lep endpoint create \
  --name private-endpoint-with-auth \
  --resource-shape cpu.tiny \
  --container-image python:3.9-slim \
  --container-port 8080 \
  --container-command 'python3 -m http.server 8080' \
  --tokens my-token-1 \
  --tokens my-token-2
```

## Invalid Usage (Will Show Error)

### ❌ Cannot use both --public and --ip-whitelist
```bash
lep endpoint create \
  --name invalid-endpoint \
  --resource-shape cpu.tiny \
  --container-image python:3.9-slim \
  --container-port 8080 \
  --container-command 'python3 -m http.server 8080' \
  --public \
  --ip-whitelist 192.168.1.0/24  # This will cause an error
```

## IP Whitelist Usage Patterns

The `--ip-whitelist` option supports two usage patterns:

### Pattern 1: Individual Values
```bash
--ip-whitelist 192.168.1.0/24 --ip-whitelist 10.0.0.0/8
```

### Pattern 2: Comma-Separated Values
```bash
--ip-whitelist "192.168.1.0/24,10.0.0.0/8,172.16.0.0/12"
```

### Pattern 3: Mixed Usage
```bash
--ip-whitelist "192.168.1.0/24,10.0.0.0/8" --ip-whitelist 172.16.0.0/12
```

## Generated JSON Structure

### Public Endpoint (no IP restrictions)
```json
{
  "spec": {
    "auth_config": {
      "ip_allowlist": []
    },
    "api_tokens": []
  }
}
```

### IP-Whitelisted Endpoint
```json
{
  "spec": {
    "auth_config": {
      "ip_allowlist": ["128.77.86.0/24", "192.168.1.0/24", "10.0.0.0/8"]
    },
    "api_tokens": [
      {
        "value_from": {
          "token_name_ref": "WORKSPACE_TOKEN"
        }
      },
      {
        "value": "my-token-1"
      },
      {
        "value": "my-token-2"
      }
    ]
  }
}
```

### Private Endpoint (default)
```json
{
  "spec": {
    "api_tokens": [
      {
        "value_from": {
          "token_name_ref": "WORKSPACE_TOKEN"
        }
      }
    ]
  }
}
```

## Key Points

1. **Clean Separation**: IP access control and authentication are completely independent
2. **IP Access Control**: Choose either `--public` OR `--ip-whitelist`, not both
3. **Authentication**: `--tokens` can be used with any IP access control method
4. **Default Behavior**: If neither `--public` nor `--ip-whitelist` is specified, the endpoint is private (no IP restrictions)
5. **IP Whitelist**: Stored in `auth_config.ip_allowlist` field
6. **Workspace Token**: Always included for non-public endpoints to maintain internal access
7. **Flexible Input**: IP whitelist accepts both individual values and comma-separated lists 