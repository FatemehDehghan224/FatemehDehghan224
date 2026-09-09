# One-time setup

This version does **not** load GitHub stats from third-party image services. The README always displays SVG files committed inside this repository.

## What updates automatically

`assets/github-stats.svg` and `assets/github-activity.svg` are regenerated from GitHub's own API by `.github/workflows/update-profile-stats.yml`:

- automatically on the first push that adds the workflow/script;
- every 6 hours afterward;
- manually from **Actions → Update profile activity → Run workflow** whenever you want.

The cards track public repositories, followers, contributions from the last 12 months, active contribution days, and the contribution calendar.

## Upload

Copy the contents of this package into the root of your profile repository (`FatemehDehghan224/FatemehDehghan224`) and push them normally.

The first push should trigger the workflow automatically. Until it finishes, the included bootstrap SVGs are shown, so the README never contains broken-image placeholders.

## If the workflow cannot push its generated SVGs

The workflow already requests only `contents: write`. If your repository-level Actions policy blocks write access, open:

**Repository Settings → Actions → General → Workflow permissions**

and allow **Read and write permissions**, then run the workflow once from the Actions tab.

## Private contributions (optional)

By default the card is designed around public GitHub activity and needs no personal access token. If you later want private contribution counts included and your GitHub privacy settings allow them, you can add a repository Actions secret named `PROFILE_TOKEN` with the appropriate GitHub user-read scope. The script automatically prefers that secret when present.

## Failure behavior

If GitHub's API is temporarily unavailable, the generator exits **before replacing the SVG files**. The README therefore keeps showing the last successful snapshot instead of a broken remote image.
