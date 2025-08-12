CONTEXT
You are an expert of the MCP protocol and your main goal is to validate servers defined in an MCP registry.
Registry is provided as a JSON document matching the MCP registry OpenAPI schema.

You can use the the mcp-validate tool according to the provided instructions in the project README file to validate each server.
You are given a list of servers generated using the registry prompt.

REQUEST:
Validate all the servers and generate an aggregated report of the errors and warnings computed by the tool.

PHASE 1: COMMAND DEFINITION
For each server, define the validation tool command using the following rules:
- use 'uv' to run it inside the dedicated venv
- use the '--env' for each environment variable defined in the registry
  - use the default value, if provided, otherwise try to guess a reasonable default according to the variable type.
  - the type is also guessed from the variable name, since there is no indication of the type in the registry schema.
  - IMPORTANT: For server-specific environment variables, follow these patterns:
    * Dynatrace: Use "https://test.apps.dynatrace.com" format (NOT .live.dynatrace.com classic URLs)
    * Database URLs: Use localhost with appropriate ports (Redis: 6379, MySQL: 3306, PostgreSQL: 5432, etc.)
    * API endpoints: Use "https://test.example.com" or similar test domains
    * Usernames: Use "test-user" or "test-username"
    * Passwords/Secrets: Use "test-password", "test-secret", "test-api-key" as appropriate
    * Tokens: Use "test-token" format
  - TRANSPORT PROTOCOL RESTRICTION: Do NOT set environment variables related to non-stdio transport protocols:
    * Do NOT set TRANSPORT_HOST, TRANSPORT_PORT, or HOST/PORT variables for stdio-based MCP servers
    * Do NOT set HTTP/TCP transport variables unless the server explicitly requires non-stdio transport
    * Most containerized MCP servers use stdio transport and don't need HOST/PORT configuration
    * Only set transport-related variables if the server documentation explicitly requires them for non-stdio transport
- use 'podman' as the runtime tool instead of 'docker'
- use '-i --rm' followed by the container name and version
- the values of additional 'package_arguments' are prepended after the container name
- use '--json-report' to generate a report named as the MCP server, with .json suffix, under new a folder named output

Command example:
uv run mcp-validate --json-report terraform-mcp-server.json -- podman run -i --rm quay.io/ecosystem-appeng/mcpserver-importer:0.1.0

PHASE 2: VALIDATION
Run the generated command and extract the relevant data from the generated report.

PHASE 3: REPORT GENERATION:
The aggregataed report includes the following fields for each server:
- Name: same as the JSON input
- Command: the command used to validate with mcp-validate tool
- Status: either Failed or Succeeded
- Errors: the computed number of validation errors
- Warnings: the computed number of validation warnings
- Report: the name of the generated JSON report

CONSTRAINTS:
- In case of error, add an Error_Message field with the brief description of the error
- The generated report is named servers_validation.json, under the output folder
- Generate an additional report in markdown format with a summary table with the validation status and errors/warnings for each server. 
  Include information on the execution timestamp.

REFERENCES:
Registry prompt: prompts/registry.md (from the project root)
Registry JSON document: output/registry.json (from the project root)
MCP protocol: https://modelcontextprotocol.io/specification/2025-06-18
MCP registry OpenAPI schema: https://github.com/modelcontextprotocol/registry/blob/main/docs/server-registry-api/openapi.yaml, 
MCP registry seed file: https://github.com/modelcontextprotocol/registry/blob/main/data/seed.json