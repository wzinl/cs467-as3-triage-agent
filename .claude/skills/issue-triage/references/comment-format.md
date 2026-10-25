# Comment format

One comment per issue, at most 1,500 characters. Write plain, friendly English. Start with
`Thanks for the report, @<author>.` and give the single reason for the comment. Then end with
this exact footer line, on its own line after a blank line:

```
_Automated first-pass triage. A maintainer will review this issue and make every decision on it._
```

Rules that `validate_plan.py` checks:

- Mention only the issue author.
- Link only https URLs on github.com, discuss.hashicorp.com, registry.terraform.io,
  developer.hashicorp.com or www.hashicorp.com.
- Reference only issues that the duplicate search returned, by their `ref` (`#123`, or `owner/repo#123` for an
  issue in another repository), never by URL.
- Do not claim to have closed, removed, assigned or prioritised anything, and do not mention any approval.

## Templates

Adapt the wording to the issue. Keep the structure.

**Possible duplicate**

```
Thanks for the report, @<author>. This looks like it may be the same request as <ref> (<short title>).
If it is, please add a 👍 and any extra details there, so the discussion stays in one place.
If it is different, a short note on how it differs will help the maintainers.

_Automated first-pass triage. A maintainer will review this issue and make every decision on it._
```

**Missing information**

```
Thanks for the report, @<author>. To reproduce this, the maintainers will need:

- <missing item 1>
- <missing item 2>

Could you add these to the issue description?

_Automated first-pass triage. A maintainer will review this issue and make every decision on it._
```

**Outdated version, or a newer release with a fix for this resource**

```
Thanks for the report, @<author>. You are on provider v<reported>, and the latest release is v<latest>.
[v<newer_fixes[0]> includes fixes for `<resource>`.]
Could you check whether this still happens on v<latest>? If it does, please add the output from that run.

_Automated first-pass triage. A maintainer will review this issue and make every decision on it._
```

**Wrong venue** (question, or a Terraform core problem)

```
Thanks for the question, @<author>. GitHub issues here are for provider bugs and feature requests.
Usage questions get faster answers on the community forum: https://discuss.hashicorp.com/c/terraform-providers/tf-aws

_Automated first-pass triage. A maintainer will review this issue and make every decision on it._
```
