# Step 6 (Bonus): GitLab Transcend Hackathon, "Life After Code"

- Platform: Devpost, managed for GitLab
- Deadline: Oct 27, 2026 @ 6:30pm IST
- Our path: **Path B: Bring Your Own**. This repo existed before Oct 5, so Path A ("must be new work") does not fit. Path B needs: the MIT-licensed source repo URL, a live deployment, and the automation + deployment done on or after Oct 5 (explain this in the submission form).
- Autonomy level: _Assisted / Supervised / Hands-off (pick one)_

## Requirements checklist

- [ ] Registered on Devpost (screenshot)
- [ ] GitLab Transcend contributor onboarding approved (screenshot)
- [ ] Public GitLab project with an MIT `LICENSE` (already in this repo)
- [ ] Uses GitLab Duo Agent Platform features: agents, flows, triggers or MCP
- [ ] Visible CI/CD pipeline history (from [.gitlab-ci.yml](../.gitlab-ci.yml))
- [ ] Demo video under 3 minutes on YouTube, public, no copyrighted music
- [ ] Text description: what it does, the problem, how GitLab automates the post-code lifecycle
- [ ] Deployed and live until ~Nov 16 (required for Path B). Google Cloud Run also earns up to +0.2 bonus, deploy code in the repo, public URL
- [ ] Submission link: _add here_

## Lifecycle stages already covered by `.gitlab-ci.yml`

The "Most Stages Covered" prize counts how many of the nine stages the automation touches.

| Stage | Covered by |
|---|---|
| plan | _Duo agent that triages new issues and turns them into MRs (to build)_ |
| create | _Duo agent / flow that writes the MR_ |
| verify | `lint`, `unit-tests` (JUnit + coverage shown in the MR) |
| package | `build-image`: builds, smoke-tests and pushes to the GitLab container registry |
| secure | SAST, Secret Detection, Dependency Scanning, Container Scanning templates |
| release | `release` job creates a GitLab Release on tags |
| configure | `deploy-cloud-run` (Google Cloud), Ansible roles in `ansible/` |
| monitor | `post-deploy-check` hits `/health`, `/version`, `/metrics` after deploy |
| govern | _Duo flow that reviews security findings against a policy and blocks or approves the MR_ |

## Ideas for the Duo agents and flows

- **Security fixer (secure):** when a scan reports a vulnerable dependency, an agent opens an MR bumping the version and links the finding.
- **Pipeline doctor (verify):** when a pipeline fails, an agent reads the job log, proposes a fix as an MR comment, and waits for approval (Assisted) or commits it (Supervised).
- **Deploy guard (monitor):** after deploy, an agent queries `/metrics`; if the error rate is above 5% it rolls back to the previous Cloud Run revision and comments on the MR.

## Google Cloud Run setup (for the bonus)

1. Create a project, enable Cloud Run, Cloud Build and Artifact Registry.
2. `gcloud artifacts repositories create notes --repository-format=docker --location=asia-south1`
3. Create a service account with Cloud Run Admin, Cloud Build Editor, Artifact Registry Writer and Service Account User. Download its JSON key.
4. In GitLab, Settings > CI/CD > Variables, add `GCP_PROJECT_ID`, `GCP_REGION` (for example `asia-south1`) and `GCP_SA_KEY` (the key, base64-encoded, masked and protected).
5. Push to the default branch. `deploy-cloud-run` and `post-deploy-check` run automatically.

## Proof of participation for CA-2

Attach to the CA-2 submission: Devpost registration screenshot, the Devpost project page or submission confirmation, the GitLab project URL, and a screenshot of a pipeline run.
