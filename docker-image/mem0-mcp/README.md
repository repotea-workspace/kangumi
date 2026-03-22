# mem0-mcp Docker Image

Builds a deployable image for the upstream `mem0-mcp-server` package.

`kangumi` intentionally does not maintain a local `Dockerfile` for this image.

The Docker image workflow builds `mem0-mcp` directly from the upstream repository context:

- `https://github.com/mem0ai/mem0-mcp.git#main`

That way the build uses the official upstream `Dockerfile` and source tree as-is, instead of duplicating the container recipe in this repository.
