# Team Roles, Ownership, and Workflow

ID Card Studio is built by a 4-person engineering team working concurrently in parallel.

---

## 1. Team Roles & Ownership

| Person | Focus Area | Owned Files & Directories |
| :--- | :--- | :--- |
| **Person 1** | Backend: AI, Data, Spec | `spec/`, `brief/`, `data/`, `generator/`, `refine/`, `storage.py`, `config.py`, `main.py`, `api/` (except render/export routes), `api/models.py`, `assets/brand_kit.py`, `templates/roles.json`, requirements base, shared scripts, contract docs, repo configs, `tests/p1/`, `docs/p1/` |
| **Person 2** | Rendering, QA, Export | `render/`, `qa/`, `export/`, `assets/photo_utils.py`, `api/routes_render.py`, `api/routes_export.py`, `api/render_models.py`, `scripts/hello_card.py`, `scripts/preview.py`, `tests/p2/`, `docs/p2/`, `requirements/p2.txt` |
| **Person 3** | Frontend (Next.js) | `frontend/` (all), `docs/p3/` |
| **Person 4** | Card Design & Data | `templates/layouts/`, `templates/themes/`, root `assets/`, `sample_data/`, `scripts/make_sample_data.py`, `tests/p4/`, `docs/p4/`, `requirements/p4.txt` |

The single source of truth for file ownership is [`docs/OWNERS.json`](file:///c:/Users/ANUBHAV/Downloads/workspace-01a11561-eca6-7528-8b22-be365d148db8/docs/OWNERS.json). Longest path match wins.

---

## 2. Team Handoffs

- **P1 → Everyone**: Design Spec schema, JSON schemas, validation loaders, and FastAPI endpoints.
- **P4 → P1 & P2**: Layout and theme starter templates (`classic.json`, `clean_light.json`) and role definitions.
- **P2 → P1 & P3**: SVG render pipeline, `/render/preview` route, and QA issue checkers.
- **P1 → P3**: Core API contract (`/brief`, `/data/upload`, `/drafts`, `/spec/patch`).
- **P4 → Everyone**: Sample data CSVs (`people_messy.csv`) and expected QA test fixtures.

---

## 3. Git Workflow & Merge Hygiene

1. **Start clean**: Before starting any task, check out fresh `main`:
   ```bash
   git checkout main
   git pull --ff-only
   git checkout -b feature/pN-<task-name>
   ```
2. **Edit only your files**: Never touch files owned by another teammate. Need an edit in another file? Message the owner to make the change in a small PR and pull it.
3. **Commit often**: Small commits with concise, informative commit messages.
4. **Pre-push verification**:
   ```bash
   git fetch origin
   git rebase origin/main
   python -m pytest
   python scripts/check_ownership.py --owner pN
   ```
   If a rebase conflict occurs, abort immediately (`git rebase --abort`) because a conflict signals that unowned files were touched.
5. **Open Pull Requests**: Push your branch and open a PR:
   ```bash
   git push -u origin feature/pN-<task-name>
   ```
   A teammate reviews; merging keeps `main` green and deployable.
   *Never force-push main.*
   *Never commit `.venv`, `.env`, `output/` files, `node_modules/`, or generated photos.*
6. **Sync after merge**: Whenever anyone merges to `main`, everyone runs:
   ```bash
   git pull --ff-only
   ```
   on `main` before starting their next task.
7. **Order**: **Person 1's foundation PR merges first** before other tasks branch out.

---

## 4. Day-1 Freeze Checklist

Every teammate must read [`docs/DESIGN_SPEC.md`](file:///c:/Users/ANUBHAV/Downloads/workspace-01a11561-eca6-7528-8b22-be365d148db8/docs/DESIGN_SPEC.md) and record these 6 items in their personal `docs/pN/` notes:

1. [ ] I understand that all lengths are in millimeters (mm) and origin `(0, 0)` is top-left of the 60 × 92 mm canvas.
2. [ ] I understand that layouts only reference theme color tokens (`background`, `primary`, etc.) and never raw hex codes.
3. [ ] I understand that card rendering is strictly deterministic code (Jinja2/SVG), not generative AI images.
4. [ ] I know which files I own per `docs/OWNERS.json` and will only edit my own files.
5. [ ] I will run `python scripts/check_ownership.py --owner pN` and `python -m pytest` before every push.
6. [ ] I agree that any breaking change to the Design Spec requires approval from all 4 team members.
