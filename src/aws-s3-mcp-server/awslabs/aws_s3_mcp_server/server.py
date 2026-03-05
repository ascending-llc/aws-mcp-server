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

"""AWS S3 MCP Server — streamable-HTTP FastMCP server for lightweight S3 operations."""

import asyncio
import os
from awslabs.aws_s3_mcp_server.consts import DEFAULT_PORT, HEARTBEAT_INTERVAL, SERVER_NAME
from awslabs.aws_s3_mcp_server.tools import register_tools
from contextlib import asynccontextmanager
from fastmcp import FastMCP
from loguru import logger
from starlette.requests import Request
from starlette.responses import JSONResponse
from typing import AsyncIterator


@asynccontextmanager
async def _lifespan(app: FastMCP) -> AsyncIterator[None]:
    """Server lifespan: starts a background heartbeat task."""
    logger.info(f'{SERVER_NAME} starting up')
    heartbeat_task = asyncio.create_task(_heartbeat())
    try:
        yield
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        logger.info(f'{SERVER_NAME} shut down')


async def _heartbeat() -> None:
    """Log a heartbeat every HEARTBEAT_INTERVAL seconds."""
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        logger.debug(f'{SERVER_NAME} heartbeat')


mcp = FastMCP(SERVER_NAME, lifespan=_lifespan)


@mcp.custom_route('/health', methods=['GET'])
async def health(request: Request) -> JSONResponse:
    """Kubernetes liveness probe endpoint."""
    return JSONResponse({'status': 'healthy', 'service': SERVER_NAME})


register_tools(mcp)


def main() -> None:
    """Run the AWS S3 MCP server."""
    port = int(os.getenv('MCP_PORT', str(DEFAULT_PORT)))
    logger.info(f'Starting {SERVER_NAME} on port {port} (streamable-http)')
    mcp.run(
        transport='streamable-http',
        host='0.0.0.0',
        port=port,
    )


if __name__ == '__main__':
    main()
