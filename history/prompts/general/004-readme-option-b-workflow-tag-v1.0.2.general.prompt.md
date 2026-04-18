---
id: "004"
title: README Option B workflow tag release
stage: general
date: 2026-04-13
surface: agent
model: claude-sonnet-4-6
feature: none
branch: 001-gurujee-foundation
user: Taimoor
command: direct prompt
labels: ["readme", "apk", "github-actions", "release", "tag", "buildozer"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - README.md
  - .github/workflows/build-apk.yml
tests:
  - none
---

## Prompt

**Option B (APK):**
            1. Download `gurujee-*.apk` below
            2. Enable Unknown Sources in Android Settings  
            3. Install the APK
            4. Open GURUJEE — guided setup runs automatically
            
            **Requirements:** Android 9+, 2GB RAM, internet for first setup
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Also upload APK as artifact (for non-tag builds)
        uses: actions/upload-artifact@v4
        with:
          name: gurujee-apk
          path: bin/*.apk

---

PART 3 — Update README.md Option B section

Replace the current Option B section with a detailed step-by-step guide and an interim "APK building..." banner.

PART 4 — Create the first GitHub release manually

After committing all files:
  git add -A
  git commit -m "feat(apk): add Kivy launcher APK, GitHub Actions build workflow"
  git tag v1.0.0
  git push origin 001-gurujee-foundation
  git push origin v1.0.0

PART 5 — Interim solution while APK builds

Update README Option B to show "APK is building automatically via GitHub Actions. Check Releases in ~20 minutes."

## Response snapshot

Updated README Option B with full step-by-step install guide and interim "APK building..." banner. Finalised build-apk.yml release body copy and artifact step name. Committed c1967d0, pushed branch. Tags v1.0.0 and v1.0.1 already existed on remote; tagged v1.0.2 and pushed — this triggers the GitHub Actions workflow with the finalised files.

## Outcome

- ✅ Impact: README Option B is accurate and user-friendly; v1.0.2 tag triggers CI build; APK will appear in Releases in ~20 min
- 🧪 Tests: none (APK build requires GitHub Actions runner)
- 📁 Files: README.md, .github/workflows/build-apk.yml
- 🔁 Next prompts: Monitor https://github.com/staimoorulhassan/GURUJEE/actions for build result; replace interim README banner with real download link once APK is published; replace placeholder logo.png
- 🧠 Reflection: Always check `git ls-remote --tags origin` before pushing a tag — remote may already have tags from prior sessions

## Evaluation notes (flywheel)

- Failure modes observed: v1.0.0 tag already existed remotely; incremented to v1.0.2 (v1.0.1 also existed)
- Graders run and results (PASS/FAIL): git push tag PASS on v1.0.2
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Add a GitHub Actions status badge to the README so build state is visible without opening Actions tab
