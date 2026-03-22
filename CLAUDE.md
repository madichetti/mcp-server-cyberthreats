# Claude Code Project Instructions

## Project Overview
MCP server for cyberthreat intelligence. See [README.md](README.md) for full details.

## Markdown Guidelines
When writing or editing markdown files:
- Wrap lines at 80–120 characters
- Always insert a final newline
- Trim trailing whitespace
- Use ordered list markers (`1.`, `2.`, etc.) for numbered lists
- Use adaptive indentation for nested lists
- Format tables consistently
- Enable preview line breaks (treat single newlines as `<br>`)
- TOC levels: 2–6 only
- Follow these markdownlint rules:
  - **MD032**: Lists should be surrounded by blank lines
  - **MD022**: Headings should be surrounded by blank lines
  - **MD047**: Files should end with a single newline
  - **MD036**: Emphasis used instead of a heading (flag this)
  - **MD026**: Trailing punctuation in headings — allowed (disabled)

## File Handling
- Treat `*.md` and `copilot-instructions.md` as markdown
- YAML/YML files (`.yaml`, `.yml`) — be conservative; avoid auto-generating or modifying unless explicitly asked
- Do not search inside `node_modules/`, `bower_components/`, or `.git/`

## Git Behavior
- Prefer smart commits (stage all tracked changes when committing)
- Do not ask to confirm sync/fetch operations
- Always create new commits rather than amending published ones

## Shell / Terminal
- Default shell on Windows: **PowerShell** (`-NoExit`)
- Use Unix-style paths in tool calls (forward slashes), but PowerShell syntax in shell scripts

## Domain Vocabulary
The following are valid project/domain terms (do not flag as spelling errors):
- **cyberthreats**, **mcp**, **cybersecurity terms**: salient, semantic, stochastic, spectrograms
- **General vocab**: altruism, adversity, resilience, authenticity, amplitude, adherence, aesthetic,
  agnostic, alleviate, amassed, aroused, aspire, attain, awareness, canary, cater, coherent,
  conduit, congenial, consistency, contemporary, conundrum, convolution, corpora, corpus,
  courtier, culmination, curated, cyclical, cynicism, subtleties, synonymous, synopsis,
  ostentatiously, overwhelm, knead, latent, quest, xenophobia, yearn, zeal, tangible, zephyr,
  stalwarts, synthesize, tranquility, brittle, burnout, preconceived, prejudice, paramount,
  permeated, perpetuate, perpetuation, persistence, perspective, pervaded, phenomenon, pivot,
  potential, precise, prevalent, primer, proactive, proliferation, prominent, proximate, pursue
