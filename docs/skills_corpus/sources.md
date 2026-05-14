# Skill sources

| Source | Format | Notes |
|---|---|---|
| `anthropics/skills` | Anthropic Skills (md + frontmatter) | Primary seed |
| `awesome-claude-skills` (community) | mixed | Filter by stars/activity before audit |
| Cursor `.cursorrules` (curated lists) | plain md | Convert to Skills frontmatter in ingestion |
| Continue.dev `.prompts` | yaml + md | Convert |
| OpenHands microagents | md + frontmatter | Closest to Skills format already |

Target seed: 200–500 skills. See [ingestion.md](ingestion.md) for the normalization step and [security_audit.md](security_audit.md) for the audit gate.
