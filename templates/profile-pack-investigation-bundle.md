# Profile Pack Investigation Bundle

> Local investigation projection only. This bundle condenses profile-pack readiness and drilldown metadata for handoff; it does not copy raw official-source bodies, mutate profile/source records, promote profiles, or certify agency compliance.

## Use

- Generate with `k-resdev profile-pack-investigation-bundle --root . --profile-id national-rnd-basic --output reports/profile-pack-investigation-bundle.md --json state/profile-pack-investigation-bundle.json`.
- Filter with `--finding-code <readiness_code>` when handing off one blocker.
- Keep human review decisions and official-source checks outside the bundle until supplied records are created.
