# Git Rules for Consistent Version Control

This document outlines the Git operational guidelines for projects using Cline. These rules ensure consistency, clarity, and maintainability in version control practices, adhering to Conventional Branch Naming and Conventional Commits standards.

## Branch Naming

### Core Standard
- **Rule**: All branch names must strictly follow the [Conventional Branch Naming](https://conventional-branch.github.io) standard.
- **Format**: Use the pattern `<type>/<short-description>`.

### Type Definition
`<type>` must be one of the following:
- **feature**: For developing new features.
- **fix**: For bug fixes in the production environment.
- **security**: For fixing security vulnerabilities.
- **docs**: For writing or updating documentation.
- **chore**: For routine tasks (e.g., updating dependencies, adjusting configurations).
- **test**: For adding or modifying test cases.
- **refactor**: For code refactoring that does not affect external behavior.
- **style**: For adjusting code style without affecting logic.
- **ci**: For modifying CI/CD processes and configurations.
- **perf**: For changes that improve performance.

### Description Definition
`<short-description>` is a brief, hyphen-separated description in English.

### Examples

#### General Examples
- `feature/implement-user-authentication`
- `fix/resolve-checkout-page-crash`
- `docs/update-installation-guide`
- `chore/upgrade-react-to-v19`

### Guidelines
- **Keep it concise and descriptive**: Branch names should clearly reflect their scope of work for traceability.
- **Avoid generic names**: Strictly avoid ambiguous names like `dev`, `test`, or `update`.
- **Use lowercase English**: All names should be in lowercase English to maintain consistency.

## Commit Messages
- **Rule**: Adhere to the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification, written in English.
- **Format**: Use the structure `<type>(<scope>): <description>`.
  - `<type>`: One of `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `style`, `ci`, or `perf`.
  - `<scope>`: The module or component affected (e.g., `auth`, `ui`, `api`).
  - `<description>`: A concise description of the change (max 50 characters recommended).
- **Examples**:
  - `feat(auth): add JWT-based user authentication`
  - `fix(ui): resolve button alignment issue on mobile`
  - `docs(readme): update installation instructions`
- **Guidelines**:
  - Write commit messages in present tense (e.g., "add" instead of "added").
  - Include a brief description of the change’s purpose and impact.
  - For complex changes, add a detailed body after a blank line, explaining *what* changed and *why*.
  - Example with body:
    ```
    feat(checkout): implement stripe payment integration

    - Added Stripe SDK and payment processing logic to handle credit card transactions on the checkout page.
    ```

## Build & Development Commands
- **Rule**: Ensure `.gitignore` is present and tailored to the project’s language and toolchain.
  - Use templates from [github/gitignore](https://github.com/github/gitignore) for common languages (e.g., Node.js, Python, Java).
  - Update `.gitignore` to exclude build artifacts, temporary files, and sensitive data (e.g., `.env`, `node_modules`).
- **Verification**: Before committing, check `.gitignore` to prevent accidental inclusion of unnecessary files.
- **Example**:
  - For a Node.js project, ensure `.gitignore` includes:
    ```
    node_modules/
    .env
    dist/
    ```

## Testing Guidelines
- **Rule**: Commit test cases alongside features or fixes to ensure code reliability.
- **Guidelines**:
  - Write unit tests for new features (`feat`) and bug fixes (`fix`).
  - Use testing frameworks consistent with the project (e.g., Jest for JavaScript, Pytest for Python).
  - Verify tests pass locally before committing.
  - Include test files in the same commit as the feature or fix for traceability.
- **Example**:
  - For `feat(auth): add JWT-based user authentication`, include `auth.test.js` with relevant test cases.

## Code Style & Guidelines
- **Rule**: Run formatters automatically via pre-commit hooks to maintain consistent code style.
- **Guidelines**:
  - Ensure all commits adhere to the project’s style guide before pushing.
  - Use tools like `husky` or `pre-commit` to automate formatting (e.g., Prettier for JavaScript, Black/Yapf/Ruff for Python).
- **Example**:
  - For a JavaScript project, run `npx prettier --write .` via pre-commit hooks.

## Documentation Guidelines
- **Rule**: Include changelogs or commit logs for release notes to maintain project transparency.
- **Guidelines**:
  - Update `CHANGELOG.md` with each release, grouping changes by `feat`, `fix`, `docs`, etc.
  - Generate release notes from commit messages using Conventional Commits structure.
  - Example `CHANGELOG.md` entry:
    ```
    ## [1.0.1] - 2025-06-16
    ### Added
    - feat(auth): add JWT-based user authentication
    ### Fixed
    - fix(ui): resolve button alignment issue on mobile
    ```
- **Automation**: Use tools like `standard-version` to automate changelog generation based on commit messages.

## Git Rules
- **Squashing Commits**:
  - Squash trivial or intermediate commits (e.g., "wip", "fix typo") before merging to maintain a clean history.
  - Use `git rebase -i` to combine commits, ensuring the final commit message follows Conventional Commits.
- **Force Push and Rebase**:
  - Warn users before suggesting `git push --force` or `git rebase` to avoid overwriting shared branches.
  - Example warning: "Force push may overwrite remote changes. Confirm branch status before proceeding."
- **Pull Requests**:
  - Create PRs for all changes, referencing the branch name and linking to relevant issues.
  - Ensure PR descriptions include a summary of changes and reference Conventional Commits.

