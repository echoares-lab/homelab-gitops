# Docker Integration with 1Password Connect

How to use 1Password Connect secrets in Docker containers.

## Pattern 1: Environment Variables at Runtime

In your service's entrypoint script:

```bash
#!/bin/bash

# Read Connect token from mounted secret
CONNECT_TOKEN=$(cat /run/secrets/op_connect_token 2>/dev/null || cat /etc/op-connect/token)
export OP_CONNECT_TOKEN=$CONNECT_TOKEN

# Fetch secret from 1Password Connect
VCENTER_PASSWORD=$(curl -s \
  -H "Authorization: Bearer ${OP_CONNECT_TOKEN}" \
  https://{connect-hostname}:8200/v1/secrets/homelab-gitops/prod/VCENTER_PASSWORD \
  | jq -r '.secret')

export VCENTER_PASSWORD

# Start application
exec "$@"
```

## Pattern 2: Docker Secrets with op run

In docker-compose.yml:

```yaml
services:
  my-service:
    image: my-image:latest
    environment:
      OP_CONNECT_TOKEN: "${OP_CONNECT_TOKEN}"
    volumes:
      - /etc/op-connect/token:/run/secrets/op_connect_token:ro
    command: |
      op run --server https://{connect-hostname}:8200 -- \
        sh -c 'python3 app.py'
```

## Pattern 3: Sidecar Pattern (Recommended)

Use an init container to fetch secrets and write to shared volume:

```yaml
services:
  my-service:
    image: my-image:latest
    depends_on:
      secrets-init:
        condition: service_completed_successfully
    volumes:
      - secrets:/run/secrets
    environment:
      # Secrets are already available in /run/secrets
      SECRET_FILE_PATH: /run/secrets/app.env

  secrets-init:
    image: alpine:latest
    environment:
      OP_CONNECT_TOKEN: "${OP_CONNECT_TOKEN}"
    volumes:
      - /etc/op-connect/token:/run/secrets/token:ro
      - secrets:/run/secrets
    command: |
      sh -c '
        CONNECT_TOKEN=$(cat /run/secrets/token)
        curl -s -H "Authorization: Bearer $CONNECT_TOKEN" \
          https://{connect-hostname}:8200/v1/secrets/homelab-gitops/prod/VCENTER_PASSWORD \
          | jq -r '"'"'.secret'"'"' > /run/secrets/app.env
        chmod 600 /run/secrets/app.env
      '

volumes:
  secrets:
    driver: local
```

## Testing

```bash
export OP_CONNECT_TOKEN=$(cat /etc/op-connect/token)
docker-compose up
docker logs my-service
# Should show application started with secrets injected
```
