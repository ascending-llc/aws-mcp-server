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

"""Tool registration hook for the AWS S3 MCP Server.

Adding a new AWS service module requires:
1. Create tools/<service>.py with a register_<service>_tools(mcp) function.
2. Add one import+call line below.
"""

from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools with the server instance."""
    from .s3 import register_s3_tools

    register_s3_tools(mcp)
    # Future — one line to add each new AWS service:
    # from .dynamodb import register_dynamodb_tools; register_dynamodb_tools(mcp)
    # from .cloudwatch import register_cloudwatch_tools; register_cloudwatch_tools(mcp)
