# lanhu-mcp Docker Image

Builds a deployable image for the upstream `dsphper/lanhu-mcp` project.

`kangumi` intentionally does not maintain a local `Dockerfile` for this image.

The Docker image workflow builds `lanhu-mcp` directly from the upstream repository context:

- `https://github.com/dsphper/lanhu-mcp.git#main`

That way the build uses the official upstream `Dockerfile` and source tree as-is.
