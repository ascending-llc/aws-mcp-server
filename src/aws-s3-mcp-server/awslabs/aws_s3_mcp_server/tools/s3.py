# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""S3 tools for the AWS S3 MCP Server."""

from awslabs.aws_s3_mcp_server.utils import get_s3_client, handle_exceptions
from fastmcp import FastMCP
from loguru import logger
from pydantic import Field
from typing import Optional


# Maximum object size returned by get-object to protect LLM context window
_GET_OBJECT_SIZE_LIMIT = 256 * 1024  # 256 KB


def register_s3_tools(mcp: FastMCP) -> None:
    """Register S3 tools with the MCP server instance."""

    @mcp.tool(name='list-objects')
    @handle_exceptions
    async def list_objects(
        bucket: str = Field(..., description='Name of the S3 bucket to list objects from.'),
        prefix: str = Field(
            '',
            description='Key prefix to filter objects. Defaults to empty string (list all objects).',
        ),
        max_keys: int = Field(
            1000,
            description='Maximum number of objects to return. Defaults to 1000.',
            ge=1,
            le=1000,
        ),
        region: Optional[str] = Field(
            None,
            description='AWS region of the bucket. Defaults to AWS_DEFAULT_REGION env var or us-east-1.',
        ),
    ) -> dict:
        """List objects in an S3 bucket.

        Returns object metadata (key, size, last_modified, etag) for all objects matching
        the given prefix. Does not return object content — use this tool for file discovery.

        Returns:
            Dict with keys:
              - objects: list of {key, size, last_modified, etag}
              - count: total number of objects returned
              - truncated: True if there are more objects beyond max_keys
        """
        logger.debug(f'list-objects: bucket={bucket!r} prefix={prefix!r} max_keys={max_keys}')
        client = get_s3_client(region)
        response = client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=max_keys)

        objects = [
            {
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'].isoformat(),
                'etag': obj.get('ETag', '').strip('"'),
            }
            for obj in response.get('Contents', [])
        ]

        return {
            'objects': objects,
            'count': len(objects),
            'truncated': response.get('IsTruncated', False),
        }

    @mcp.tool(name='list-buckets')
    @handle_exceptions
    async def list_buckets(
        region: Optional[str] = Field(
            None,
            description='AWS region for the API call. Defaults to AWS_DEFAULT_REGION env var or us-east-1.',
        ),
    ) -> dict:
        """List all S3 buckets in the AWS account.

        Returns bucket names and creation dates. Note that S3 bucket listing is
        account-wide — all buckets across all regions are returned.

        Returns:
            Dict with keys:
              - buckets: list of {name, creation_date}
              - count: total number of buckets
        """
        logger.debug('list-buckets')
        client = get_s3_client(region)
        response = client.list_buckets()

        buckets = [
            {
                'name': b['Name'],
                'creation_date': b['CreationDate'].isoformat(),
            }
            for b in response.get('Buckets', [])
        ]

        return {
            'buckets': buckets,
            'count': len(buckets),
        }

    @mcp.tool(name='head-object')
    @handle_exceptions
    async def head_object(
        bucket: str = Field(..., description='Name of the S3 bucket.'),
        key: str = Field(..., description='S3 key of the object to inspect.'),
        region: Optional[str] = Field(
            None,
            description='AWS region of the bucket. Defaults to AWS_DEFAULT_REGION env var or us-east-1.',
        ),
    ) -> dict:
        """Get metadata for an S3 object without fetching its content.

        Use this to check whether an object exists, its size, content type,
        and last modified time — without consuming context window on its content.

        Returns:
            Dict with keys:
              - uri: S3 URI of the object
              - exists: True
              - size: size in bytes
              - content_type: MIME type
              - last_modified: ISO 8601 timestamp
              - etag: ETag of the object
        """
        logger.debug(f'head-object: bucket={bucket!r} key={key!r}')
        client = get_s3_client(region)
        response = client.head_object(Bucket=bucket, Key=key)

        return {
            'uri': f's3://{bucket}/{key}',
            'exists': True,
            'size': response['ContentLength'],
            'content_type': response.get('ContentType', ''),
            'last_modified': response['LastModified'].isoformat(),
            'etag': response.get('ETag', '').strip('"'),
        }

    @mcp.tool(name='get-object')
    @handle_exceptions
    async def get_object(
        bucket: str = Field(..., description='Name of the S3 bucket.'),
        key: str = Field(..., description='S3 key of the object to read.'),
        region: Optional[str] = Field(
            None,
            description='AWS region of the bucket. Defaults to AWS_DEFAULT_REGION env var or us-east-1.',
        ),
    ) -> dict:
        """Read the text or JSON content of a small S3 object.

        Only suitable for text-based objects (application/json, text/*) up to 256 KB.
        Binary objects and objects exceeding the size limit are rejected — use
        agent-local boto3 tools for those.

        Returns:
            Dict with keys:
              - uri: S3 URI of the object
              - content: decoded string content
              - content_type: MIME type
              - size: size in bytes
              - last_modified: ISO 8601 timestamp
        """
        logger.debug(f'get-object: bucket={bucket!r} key={key!r}')
        client = get_s3_client(region)

        # Check size and content type before fetching content
        head = client.head_object(Bucket=bucket, Key=key)
        size = head['ContentLength']
        content_type = head.get('ContentType', '')

        if size > _GET_OBJECT_SIZE_LIMIT:
            return {
                'error': (
                    f'Object is {size:,} bytes — exceeds the {_GET_OBJECT_SIZE_LIMIT // 1024} KB '
                    'limit for get-object. Use agent-local boto3 tools for large files.'
                ),
                'code': 'ObjectTooLarge',
                'tool': 'get-object',
            }

        if content_type != 'application/json' and not content_type.startswith('text/'):
            return {
                'error': (
                    f'Object content type {content_type!r} is not text-based. '
                    'Use agent-local boto3 tools for binary objects.'
                ),
                'code': 'UnsupportedContentType',
                'tool': 'get-object',
            }

        response = client.get_object(Bucket=bucket, Key=key)
        with response['Body'] as body:
            content = body.read().decode('utf-8')

        return {
            'uri': f's3://{bucket}/{key}',
            'content': content,
            'content_type': content_type,
            'size': size,
            'last_modified': head['LastModified'].isoformat(),
        }

    @mcp.tool(name='create-presigned-url')
    @handle_exceptions
    async def create_presigned_url(
        bucket: str = Field(..., description='Name of the S3 bucket.'),
        key: str = Field(..., description='S3 key of the object.'),
        expires_in: int = Field(
            3600,
            description='URL expiry time in seconds. Defaults to 1 hour. Maximum 7 days (604800).',
            ge=1,
            le=604800,
        ),
        region: Optional[str] = Field(
            None,
            description='AWS region of the bucket. Defaults to AWS_DEFAULT_REGION env var or us-east-1.',
        ),
    ) -> dict:
        """Generate a presigned URL for temporary read access to an S3 object.

        The URL allows anyone with the link to download the object without AWS
        credentials — useful for sharing reports or artifacts with end users.

        Returns:
            Dict with keys:
              - url: presigned HTTPS URL
              - uri: S3 URI of the object
              - expires_in: expiry duration in seconds
        """
        logger.debug(
            f'create-presigned-url: bucket={bucket!r} key={key!r} expires_in={expires_in}'
        )
        client = get_s3_client(region)
        url = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expires_in,
        )

        return {
            'url': url,
            'uri': f's3://{bucket}/{key}',
            'expires_in': expires_in,
        }

    @mcp.tool(name='put-object')
    @handle_exceptions
    async def put_object(
        bucket: str = Field(..., description='Name of the S3 bucket to write the object to.'),
        key: str = Field(..., description='S3 key (path) for the object.'),
        content: str = Field(
            ...,
            description='String content to write. Must be text or JSON — binary content is not supported.',
        ),
        content_type: str = Field(
            'application/json',
            description=(
                'MIME type of the content. Must be "application/json" or start with "text/" '
                '(e.g. "text/plain", "text/csv"). Binary content types are rejected.'
            ),
        ),
        region: Optional[str] = Field(
            None,
            description='AWS region of the bucket. Defaults to AWS_DEFAULT_REGION env var or us-east-1.',
        ),
    ) -> dict:
        """Write string or JSON content to an S3 object.

        Accepts text and JSON content types only (application/json or text/*).
        Binary content types are rejected at the tool level — Parquet and other binary
        writes should be performed using boto3 directly in agent-local tools.

        Returns:
            Dict with keys:
              - uri: S3 URI of the written object (s3://bucket/key)
              - etag: ETag of the written object
        """
        if content_type != 'application/json' and not content_type.startswith('text/'):
            return {
                'error': (
                    f'Unsupported content_type: {content_type!r}. '
                    'Only "application/json" and "text/*" are accepted. '
                    'Binary writes must be performed via boto3 in agent-local tools.'
                ),
                'code': 'UnsupportedContentType',
                'tool': 'put-object',
            }

        logger.debug(f'put-object: bucket={bucket!r} key={key!r} content_type={content_type!r}')
        client = get_s3_client(region)
        response = client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content.encode('utf-8'),
            ContentType=content_type,
        )
        etag = response.get('ETag', '').strip('"')

        return {
            'uri': f's3://{bucket}/{key}',
            'etag': etag,
        }
