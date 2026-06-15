"""What the generator downloads: the chasqui-stack repos at a pinned tag.

The stack tag is pinned per CLI release (ADR-005): CLI v0.1.0 scaffolds the
services at v0.1.0. `chasqui new --ref <branch|tag>` overrides it for
development against unreleased branches.
"""

ORG = "chasqui-stack"

# Stack tag this CLI release scaffolds. Bumped together with the CLI version.
STACK_TAG = "v0.2.4"

# target directory in the generated project -> GitHub repo name.
# Always-present services + channel gateways (the wizard picks which channels).
SERVICES = {
    "core": "core",
    "admin": "admin",
}

# Channel gateways — fetched only when selected in the wizard (Answers.channels).
CHANNEL_SERVICES = {
    "whatsapp": "whatsapp",
    "telegram": "telegram",
}

# The parent repo contributes root files to the generated project.
PARENT_REPO = "chasqui"
PARENT_ROOT_FILES = ["docker-compose.yml"]

CODELOAD_URL = "https://codeload.github.com/{org}/{repo}/tar.gz/{ref}"
