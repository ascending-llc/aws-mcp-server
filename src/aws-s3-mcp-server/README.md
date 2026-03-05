# AWS S3 MCP Server

An [AWS Labs MCP](https://awslabs.github.io/mcp/) server that exposes lightweight Amazon S3 operations over streamable-HTTP transport for use by AI agents and orchestrators.

## Tools

| Tool | Description |
|------|-------------|
| `list-buckets` | List S3 buckets visible to the configured AWS credentials. Returns bucket name and creation date only. |
| `list-objects` | List objects in an S3 bucket — returns metadata only (key, size, last_modified, etag). Designed for file discovery without consuming LLM context. |
| `head-object` | Retrieve metadata for a single S3 object (size, ETag, content type) without downloading the body. Useful for existence checks and validating object properties. |
| `get-object` | Read small text or JSON objects from S3. Limited to 256 KB and `text/*` / `application/json` content types. Use presigned URLs or AWS SDKs for large or binary objects. |
| `put-object` | Write string or JSON content to an S3 object. Accepts `application/json` and `text/*` content types only. Binary writes must be performed via boto3 directly. |
| `create-presigned-url` | Generate a short-lived presigned URL for temporary read access to an S3 object. Expiry is configurable up to 7 days (default 1 hour). |

## Transport

This server uses **streamable-HTTP** transport on port `3334` (configurable via `MCP_PORT` env var):

- `GET /mcp` — SSE stream for tool discovery
- `POST /mcp` — tool call requests
- `GET /health` — liveness probe (`{"status": "healthy", "service": "aws-s3-mcp"}`)

## Authentication

Uses the boto3 default credential chain. In Kubernetes, configure [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html) (IAM Roles for Service Accounts) so the pod automatically receives the appropriate S3 permissions — no credential passing required.

Region defaults to `AWS_DEFAULT_REGION` env var, then `AWS_REGION`, then `us-east-1`.

## Running Locally

```bash
cd src/aws-s3-mcp-server
uv venv && uv sync --all-groups
uv run python -m awslabs.aws_s3_mcp_server.server

# Verify health
curl http://localhost:3334/health
```

## Running Tests

```bash
cd src/aws-s3-mcp-server
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing
```

## Architecture

Tools are registered via an extensibility hook in `tools/__init__.py`. Adding a new AWS service requires:

1. Create `tools/<service>.py` with a `register_<service>_tools(mcp)` function.
2. Add one import + call line to `tools/__init__.py`.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
