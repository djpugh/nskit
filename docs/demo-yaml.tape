# nskit Demo — YAML Input
# Run: vhs docs/demo-yaml.tape
# Produces: docs/assets/demo-yaml.gif

Output docs/source/assets/demo-yaml.gif

Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"


Type "# nskit — initialise a project from a YAML config"
Enter
Sleep 1s

Enter

Type "# Step 1: List recipes"
Enter
Type "nskit list"
Enter
Sleep 3s

Enter

Type "# Step 2: Create input YAML"
Enter
Type "cat > /tmp/nskit-input.yaml << 'EOF'"
Enter
Type "name: my-awesome-project"
Enter
Type "repo:"
Enter
Type "  owner: Demo User"
Enter
Type "  email: demo@example.com"
Enter
Type "  description: Created with nskit"
Enter
Type "  url: github.com/demo/my-awesome-project"
Enter
Type "EOF"
Enter
Sleep 1s

Enter

Type "# Step 3: Initialise from YAML"
Enter
Type "nskit init --recipe python_package --input-yaml-path /tmp/nskit-input.yaml --output-base-path /tmp/nskit-demo"
Enter
Sleep 4s

Enter

Type "# Step 4: Check the pyproject.toml"
Enter
Type "head -15 /tmp/nskit-demo/my-awesome-project/pyproject.toml"
Enter
Sleep 3s

Type "rm -rf /tmp/nskit-demo /tmp/nskit-input.yaml"
Enter

Enter

Type "# YAML mode — great for CI/CD and scripting."
Enter
Sleep 2s
