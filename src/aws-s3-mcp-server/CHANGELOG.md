# Changelog

## 0.1.0 (2026-03-02)

### Features

- Initial release of `awslabs.aws-s3-mcp-server`
- `list-objects` tool: list S3 bucket objects by prefix, returning metadata only (key, size, last_modified, etag)
- `put-object` tool: write text/JSON artifacts to S3; binary content types rejected at tool level
- Streamable-HTTP transport on port 3334 for Kubernetes ClusterIP deployment
- `/health` liveness probe endpoint
- Extensible tool registration hook in `tools/__init__.py`
- IRSA-compatible authentication via boto3 default credential chain
