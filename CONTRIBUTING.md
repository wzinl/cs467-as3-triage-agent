# Contributing

This repository is a sandbox: a pinned subset of the Terraform AWS Provider plus an issue-triage agent and
its evaluation. Contributions to the provider itself belong upstream, in
[hashicorp/terraform-provider-aws](https://github.com/hashicorp/terraform-provider-aws). `AGENTS.md` has the
layout, the commands and the rules for this repository.

## Changes to the triage agent

- **Behaviour**: the procedure is in `.claude/skills/issue-triage/SKILL.md`, the comment rules in its
  `references/comment-format.md`.
- **Limits** (trigger, permissions, model, tools, budgets, safe outputs): edit the frontmatter of
  `.github/workflows/issue-triage.md`, run `gh aw compile issue-triage` with the gh-aw version named in the lock
  file, and commit the `.md` and the regenerated `.lock.yml` together. Never edit the lock file by hand.
- Every change to the workflow or the skill must pass `python3 -m unittest discover -s .claude/skills/issue-triage/tests`,
  and its PR must say how the change was tried (a run on a test issue in this repository's Actions).
- A change that widens what the agent can do (permissions, tools, network access, safe outputs, budgets) must
  say so in the PR description, with the reason. `.github/CODEOWNERS` requests the owner's review. This
  sandbox has one maintainer, so nothing blocks the owner's own merge; upstream, branch protection would.

## AI-contribution policy

This project follows the upstream [AI usage policy](docs/ai-usage.md): transparency, accountability and quality.
The rules below add what applies here, both to people who use AI tools and to the triage agent itself.

**People using AI tools**

- State in the PR description which parts an AI tool wrote or changed. Add `🤖🤖🤖` to the title when an
  agent opened the PR, as the upstream policy asks.
- The human who opens the PR owns every line and must be able to explain it without the tool's help.
- Do not paste AI output into issues or reviews unedited. Upstream maintainers have already had to apologise
  for a confident but wrong AI-written answer on an issue (upstream #48821).
- Never give an AI tool repository secrets, or write access it does not need for the task.

**The triage agent**

- It is a bot and says so: it posts as `github-actions[bot]`, its comment ends with a fixed line saying a
  maintainer makes every decision, and gh-aw adds a footer that links the workflow run.
- It only suggests. It may add at most three allow-listed labels and post at most one comment on the issue it was
  run for. It cannot close, lock, edit, assign, remove labels, open issues, merge or push. The workflow's permissions
  and safe outputs enforce these limits; its instructions only repeat them.
- Maintainers make every decision: `needs-triage`, priority, duplicates, closing. Treat a wrong label or comment
  from the agent like any triage mistake: fix it, then open an issue that links it so it can become a test case.
- To stop it at once, add the label `triage-agent-paused` to any issue. New runs are skipped while any issue
  carries it, and the workflow stops by itself on the date in its lock file (`stop-after`). To stop a run
  already going, cancel it in the Actions tab; disabling the workflow there stops every trigger.
- Its prompts, tool calls and outputs are kept as artifacts of each workflow run. Its model is pinned in the workflow.

## Reporting a security issue

Do not open a public issue. Follow https://www.hashicorp.com/security for the provider. For this sandbox,
contact the repository owner privately.
