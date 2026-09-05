# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-07-15

### Added
- **UI Design System (Stitch MCP)**: Designed 6 new mockups representing the core Munim.ai product:
  - CA Dashboard (Dark and Light modes)
  - CA Dashboard Sub-tabs: Supplier Trust, Action Queue, Monthly Reports (Light Mode)
  - Trader PWA Home (Mobile, Light and Dark modes)
  - Login Page with language support (Light Mode)
- **Business Case**: Drafted `munim_business_case.md` factbook with quantified GST ecosystem facts, TAM/SAM/SOM market analysis, cost structures, and competitive landscape.

### Fixed
- **MCP Servers Configurations**: Addressed persistent path issues across all MCP servers (Stitch, Supabase, Github, Memory, Puppeteer) by pointing them to absolute paths for `node.exe` and `npx-cli.js`.

### Changed
- **Git Hygiene**: Updated `.gitignore` to omit unnecessary logging (`logs/`), remote configuration (`mcp-remote`), ngrok remnants, and `config.yml`.
