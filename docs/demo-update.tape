# nskit Demo — Update Workflow (3-way merge)
# Shows: init → customise → check → update → see merge result
# Run: vhs docs/demo-update.tape
# Produces: docs/source/assets/demo-update.gif

Output docs/source/assets/demo-update.gif

Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"

Env "RECIPE_REPO_OWNER" "Demo User"
Env "RECIPE_REPO_EMAIL" "demo@example.com"


Type "# nskit Update — 3-way merge preserves your changes"
Enter
Sleep 1s

Enter

Type "# Step 1: Init a project interactively"
Enter
Type "nskit init --recipe python_package --output-base-path /tmp/nskit-update"
Enter
Sleep 2s

# Answer the prompts
Type "update-demo"
Enter
Sleep 1s

# Accept default (RECIPE_REPO_OWNER)
Enter
Sleep 1s

# Accept default (RECIPE_REPO_EMAIL)
Enter
Sleep 1s

Type "github.com/demo/update-demo"
Enter
Sleep 4s

Enter

Type "# Step 2: Customise it (add your own content to README)"
Enter
Type "echo '' >> /tmp/nskit-update/update-demo/README.md"
Enter
Type "echo '## My Custom Section' >> /tmp/nskit-update/update-demo/README.md"
Enter
Type "echo 'This is content I added after init.' >> /tmp/nskit-update/update-demo/README.md"
Enter
Type "cat /tmp/nskit-update/update-demo/README.md"
Enter
Sleep 3s

Enter

Type "# Step 3: Commit the customisation"
Enter
Type "cd /tmp/nskit-update/update-demo && git add . && git commit -m 'Add custom section' --no-verify -q"
Enter
Sleep 1s

Enter

Type "# Step 4: Check for updates"
Enter
Type "nskit --backend docker-local check --project-path /tmp/nskit-update/update-demo"
Enter
Sleep 2s

Enter

Type "# Step 5: Update (3-way merge dry run)"
Enter
Type "nskit --backend docker-local update --project-path /tmp/nskit-update/update-demo --dry-run"
Enter
Sleep 3s

Enter

Type "# Your custom section is preserved. Recipe changes are applied."
Enter
Sleep 1s

Type "cat /tmp/nskit-update/update-demo/README.md"
Enter
Sleep 3s

Enter

Type "# Clean up"
Enter
Type "rm -rf /tmp/nskit-update"
Enter

Enter

Type "# Init → customise → update. Your work survives."
Enter
Sleep 2s
