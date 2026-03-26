# nskit Demo — Docker Mode (local images)
# Shows: build image with labels → discover via CLI → init interactively
# Run: vhs docs/demo-docker.tape
# Produces: docs/source/assets/demo-docker.gif

Output docs/source/assets/demo-docker.gif

Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"

Env "RECIPE_REPO_OWNER" "Demo User"
Env "RECIPE_REPO_EMAIL" "demo@example.com"


Type "# nskit Docker Mode — discover recipes from local Docker images"
Enter
Sleep 1s

Enter

Type "# Step 1: Build a recipe image with nskit labels"
Enter
Type "docker build --target runtime --build-arg RECIPE_NAME=python_package -t nskit/python_package:v1.0.0 . -q"
Enter
Sleep 8s

Enter

Type "# Step 2: List recipes (discovered from Docker labels)"
Enter
Type "nskit --backend docker-local list"
Enter
Sleep 3s

Enter

Type "# Step 3: Init project interactively (runs inside the container)"
Enter
Type "nskit --backend docker-local init --recipe python_package --output-base-path /tmp/nskit-docker"
Enter
Sleep 2s

# Answer the prompts
Type "docker-project"
Enter
Sleep 1s

# Accept default (RECIPE_REPO_OWNER)
Enter
Sleep 1s

# Accept default (RECIPE_REPO_EMAIL)
Enter
Sleep 1s

Type "github.com/company/docker-project"
Enter
Sleep 10s

Enter

Type "# Clean up"
Enter
Type "rm -rf /tmp/nskit-docker"
Enter
Type "docker rmi nskit/python_package:v1.0.0 2>/dev/null"
Enter

Enter

Type "# Label images → discover locally → init interactively → runs in containers."
Enter
Sleep 2s
