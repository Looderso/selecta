# SESSION_RULES.md

This file contains session-specific rules and instructions for Claude Code to follow when working on the Selecta project.

## Current Session Focus
<!-- Specify the current development focus, e.g., "Fixing YouTube integration bugs" -->
Token optimization and efficient code navigation

## Token Optimization Rules
1. **Documentation-First Approach**
   - Always consult documentation before reading code files
   - Follow the documentation hierarchy (top-level → module → component)
   - Use CODE_INDEX.md as your primary navigation tool
   - Only read code files after understanding their context through documentation

2. **Search Optimization**
   - Avoid broad searches across the entire codebase
   - Use targeted searches based on documentation guidance
   - Search within specific files or directories identified by documentation
   - Prefer navigating through documentation links over search operations

3. **File Reading Strategy**
   - Read only the files necessary for your task
   - Focus on relevant sections rather than entire files
   - Use documentation to identify the specific components you need
   - Scan file structure and imports before reading the entire content

4. **Batch Operations**
   - Use BatchTool to run multiple operations in parallel
   - Group related file reads to minimize context switching
   - Combine related edits into a single message when possible
   - Make multiple small, focused changes rather than large, sweeping ones

5. **Code Comprehension**
   - Understand the architecture through documentation first
   - Look for patterns and conventions in similar code
   - Focus on interfaces and public APIs before implementation details
   - Use documentation to understand component relationships

## Documentation and File Access Workflow
1. Start by consulting these top-level guides:
   - CLAUDE.md: General project information and token optimization strategy
   - CODE_INDEX.md: Quick reference to find key files and documentation
   - SESSION_RULES.md (this file): Session-specific rules

2. Once you identify the relevant module, check the module documentation:
   - Each module has a README.md file with detailed information
   - Module READMEs help locate specific files for particular functionality
   - Read module documentation completely before examining any code

3. File access sequence:
   - Use CODE_INDEX.md to locate the relevant module
   - Check module README.md for architecture and component understanding
   - Review sub-module README.md for specific component details
   - Only then start reading and modifying actual code files
   - Use precise, targeted searches based on documentation guidance

4. After making changes, update documentation:
   - Update any affected module README.md files when component functionality changes
   - Update CODE_INDEX.md if new files or major structural changes are made
   - Document significant changes in the Change History section of relevant README.md files
   - Ensure your changes are consistent with the documented architecture and patterns

## Session-Specific Rules
<!-- Add any specific rules for this session -->
1.
2.
3.

## Code Style Rules
- Follow Python type hints strictly
- Maintain consistent error handling patterns
- Use SQLAlchemy 2.0 style for database operations

## Testing Requirements
<!-- Specify any testing requirements for this session -->
- Run appropriate tests after modifications
- Use `ruff check src` to verify code quality

## Notes
<!-- Add any other information Claude should know -->
