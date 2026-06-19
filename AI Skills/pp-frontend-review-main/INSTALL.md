# Installing pp-frontend-review

Three install paths depending on the team's tooling and rollout speed.

## Path A — Individual install (Claude Code, fastest)

If a developer received `pp-frontend-review.plugin` directly:

1. Open Claude Code.
2. Drop the `.plugin` file into the Claude Code window, or run:
   ```
   claude plugin add ./pp-frontend-review.plugin
   ```
3. Confirm install when prompted.
4. Verify with:
   ```
   You: list installed plugins
   ```
   `pp-frontend-review` should appear with six skills, one orchestrator, and three agents.

5. Try it:
   ```
   You: review the current branch against main
   ```

## Path B — Team rollout via private marketplace

This is the recommended way to make `pp-frontend-review` a standard practice across a team. Every developer installs once; updates flow automatically.

### One-time: publish the marketplace

1. Create a private Git repo (e.g., `paypal/claude-marketplace`) accessible to your team.
2. At the marketplace root, add `marketplace.json`:

   ```json
   {
     "name": "paypal-marketplace",
     "owner": "PayPal",
     "plugins": [
       {
         "name": "pp-frontend-review",
         "source": "./plugins/pp-frontend-review",
         "version": "1.0.0",
         "description": "Staff-engineer frontend code review for React/Next.js/Node."
       }
     ]
   }
   ```

3. Place the unzipped `pp-frontend-review/` directory at `plugins/pp-frontend-review/` in that repo.
4. Commit and push.

### Per-developer: add the marketplace and install

```
claude plugin marketplace add git+ssh://git@github.com/paypal/claude-marketplace.git
claude plugin add pp-frontend-review --marketplace paypal-marketplace
```

### Per-repo (optional): auto-load on frontend repos

In any frontend repo, commit `.claude/settings.json`:

```json
{
  "extensions": ["pp-frontend-review"]
}
```

Now anyone who opens this repo in Claude Code with the marketplace configured gets the review skills enabled automatically.

### Updating

Bump `version` in the plugin's `plugin.json` and the marketplace `marketplace.json`. Push. Devs run:

```
claude plugin update pp-frontend-review
```

## Verifying the install

In any repo:

```
You: list available skills
```

You should see (Claude Code):
- `code-review-and-quality`
- `code-simplification`
- `security-and-hardening`
- `performance-optimization`
- `frontend-ui-engineering`
- `pp-react-suggestion`
- `review-frontend`

And agents:
- `code-reviewer`
- `security-auditor`
- `test-engineer`

Then:

```
You: review-frontend on the current branch
```

The orchestrator should detect the framework, run lint/typecheck/test where available, run the six skills, and emit a consolidated severity-tagged report ending in `VERDICT: APPROVE` or `VERDICT: REQUEST CHANGES`.

## Troubleshooting

- **Plugin doesn't appear after install** — restart Claude Code.
- **`review-frontend` doesn't trigger** — invoke explicitly with the skill name, then file an issue if natural language phrasing fails.
- **`npm audit` reports dev-only issues** — orchestrator runs `--omit=dev` to keep noise down. To audit dev deps, run manually.

## Removing

```
claude plugin remove pp-frontend-review
```
