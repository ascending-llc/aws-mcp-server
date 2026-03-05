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

"""Common utilities and helpers for the AWS S3 MCP Server."""

import boto3
import os
from awslabs.aws_s3_mcp_server import __version__
from awslabs.aws_s3_mcp_server.consts import DEFAULT_REGION
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError
from functools import wraps
from typing import Optional, Tuple


def _user_agent_extra() -> str:
    return f'awslabs/mcp/aws-s3-mcp-server/{__version__}'


def get_s3_client(region_name: Optional[str] = None) -> BaseClient:
    """Create a boto3 S3 client.

    Args:
        region_name: Optional AWS region name. If not provided, uses AWS_DEFAULT_REGION
                    environment variable or falls back to us-east-1.

    Returns:
        Configured boto3 S3 client.
    """
    region = (
        region_name or os.getenv('AWS_DEFAULT_REGION') or os.getenv('AWS_REGION') or DEFAULT_REGION
    )
    config = Config(user_agent_extra=_user_agent_extra())
    session = boto3.Session()
    return session.client('s3', region_name=region, config=config)


def handle_exceptions(func):
    """Decorator to handle exceptions consistently across tools.

    Returns a structured error dict on failure — never raises.
    Error dict shape: {"error": str(e), "code": "<boto3 error code>", "tool": func.__name__}
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code', 'UnknownError')
            return {'error': str(e), 'code': code, 'tool': func.__name__}
        except Exception as e:
            return {'error': str(e), 'code': type(e).__name__, 'tool': func.__name__}

    return wrapper


def parse_s3_uri(uri: str) -> Tuple[str, str]:
    """Parse an S3 URI into (bucket, key).

    Args:
        uri: S3 URI in the form s3://bucket/key

    Returns:
        Tuple of (bucket, key).

    Raises:
        ValueError: If the URI is not a valid s3:// URI.
    """
    if not uri.startswith('s3://'):
        raise ValueError(f"Invalid S3 URI: '{uri}'. Must start with 's3://'")

    without_scheme = uri[5:]
    if '/' in without_scheme:
        bucket, key = without_scheme.split('/', 1)
    else:
        bucket = without_scheme
        key = ''

    if not bucket:
        raise ValueError(f"Invalid S3 URI: '{uri}'. Missing bucket name.")

    return bucket, key
