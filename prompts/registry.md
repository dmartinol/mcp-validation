CONTEXT:
You are an expert of the MCP protocol and your main goal is to register servers in the MCP registry.
Servers are defined in JSON document including:
- the logical name
- the URL of the code repository
- the URL of the container image
- the MCP transport protocol:
  - one or more of stdio, http, sse (separated by /)
  - N/A if no protocol information is available

REQUEST:
Given the description of the servers according to the provided schema, generate a registry configuration for an
MCP registry, according to the MCP registry OpenAPI schema, for each server in the provided list.

PHASE 1: CLONE SERVER REPO
Clone the server in a temporary folder 'tmp_servers' at the root of the project.

PHASE 2: EXTRACT SERVER METADATA:
Retrieve relevant information from the cloned repository README file to define the server metadata:
- id: generate a random ID in uuid format
- name: same as the original name in the input document
- description: a short description from the README
- repository: 
  - url: the original repo URL
  - source: set to "github"
  - id: the GitHub repository ID using the id field from 'https://api.github.com/repos/<ORGANIZATION>/<REPO>'
- version_detail: 
  - version: parse the Repo field of the input JSON and extract the version after the last ':'. E.g., for 
  'quay.io/validated-mcp-servers/elasticsearch:20250809-5014d91', version is '20250809-5014d91'
  - release_date: set it to today's date for now
  - is_latest: alwasy set to 'true'

PHASE 3: EXTRACT PACKAGES DATA
The packages data must include a single entry of type "docker", with the following details:
- registry_name: set to 'docker'
- name: name of the container image from the input JSON, without the version tag.
- version: the version tag from the container image in the input JSON
- environment_variables: extract environment variables that can configure the behavior of the MCP server. Follow these guidelines:
  * CRITICAL: Extract exact variable names as documented in the README file - do NOT assume standard naming conventions
  * Look for variables in configuration examples, command line examples, and environment variable sections
  * Verify variable names against code examples, Docker commands, and configuration samples in the README
  * If the README shows `-e VARIABLE_NAME` in Docker commands, use exactly that variable name
  * Do NOT invent or standardize variable names - use only what is explicitly documented
  For each documented environment variable add an entry with:
  - name: exact variable name as documented (respect exact case and spelling from README)
  - description: short description based on documentation
  - is_required: whether it's a mandatory variable or not. In case of uncertainty, omit this field
  - default: possible default value if explicitly stated. In case of uncertainty, omit this field
  - is_secret: use 'true' if the variable seems to define a sensitive secret. Include variables defining a username. In case of uncertainty, omit this field
  - choices: list of possible values for the input if explicitly documented. If no choices are given, omit this field
- package_arguments: if any additional argument needs to be executed (e.g., in `docker run docker.elastic.co/mcp/elasticsearch stdio`, 'stdio' is the package argument)
  add one entry for each of them with:
    - description: short description based on documentation
    - is_required: whether it's a mandatory variable or not. In case of uncertainty, omit this field
    - format: set to "string"
    - value: the desired value from the documentatino (e.g. "stdio")
    - type: "named" or "positional", according to the documentation. For "named" arguments, the "name" field is also needed.
    - name: optional argument name (only for "named" arguments)

PHASE 4: GENERATE REGISTRY DEFINITION
Assemble all the information collected and store the definition in a registry.json file at the root of the project.
Always use this name to store the configuration.

CONSTRAINTS:
- The generated file must match the MCP registry OpenAPI schema
- If no container image has been defined (e.g., the Repo field in the JSON input does not link to a container image):
  - Set 'N/A' in the version field of version_details
  - Set an empty the packages definition

REFERENCES:
MCP protocol: https://modelcontextprotocol.io/specification/2025-06-18
MCP registry OpenAPI schema: https://github.com/modelcontextprotocol/registry/blob/main/docs/server-registry-api/openapi.yaml, 
MCP registry seed file: https://github.com/modelcontextprotocol/registry/blob/main/data/seed.json