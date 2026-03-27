# nskit Demo — Interactive CLI
# Run: vhs docs/demo-local.tape
# Produces: docs/assets/demo-local.gif

Output docs/source/assets/demo-local.gif

Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"

Env "RECIPE_REPO_OWNER" "Demo User"
Env "RECIPE_REPO_EMAIL" "demo@example.com"


Type "# nskit — composable project recipes with 3-way merge updates"
Enter
Sleep 1s

Enter

Type "# Step 1: See what recipes are available"
Enter
Type "nskit list"
Enter
Sleep 3s

Enter

Type "# Step 2: Check what fields a recipe needs"
Enter
Type "nskit get-required-fields --recipe python_package"
Enter
Sleep 3s

Enter

Type "# Step 3: Initialise a project interactively"
Enter
Type "nskit init --recipe python_package --output-base-path /tmp/nskit-demo"
Enter
Sleep 2s

# Answer the prompts
Type "my-awesome-project"
Enter
Sleep 1s

# Accept defaults for owner and email (set via RECIPE_ env vars)
Enter
Sleep 1s

Enter
Sleep 1s

Type "github.com/demo/my-awesome-project"
Enter
Sleep 4s

Enter

Type "# Done! Project created with tree output above."
Enter
Sleep 2s

Type "rm -rf /tmp/nskit-demo"
Enter
