# Delhi NCR job search — assets & trackers

Built from the content published on [ratan-patel.github.io](https://ratan-patel.github.io/).
Nothing here invents experience: every claim traces back to the CV / site text.

| File | What it is | Use it for |
|---|---|---|
| `Ratan_Kumar_Patel_CV_2026.pdf` | 1-page, **text-based** (ATS-parsable) CV | Attach to every application |
| `build_cv.py` | Generator for the CV (`python3 job-search/build_cv.py`) | Edit content once, rebuild |
| `applications-email.md` | 25 ready-to-send emails — company-specific hook + subject line each | Copy/paste into Gmail |
| `applications.csv` | Same 25 rows as a spreadsheet | Import into Sheets, track replies |
| `build_outreach.py` | Single source of truth for the company list; regenerates the `.md`, `.csv` and the table inside `portfolio.html` | Add/remove companies |

Public dashboard: **https://ratan-patel.github.io/portfolio.html** → *Applications* section
(filter by training institute vs security firm, search, copy all emails, export CSV).

## Why a new CV PDF
`ratan_patel_cv.pdf` at the repo root is an image-based PDF — no selectable text, and ATS
parsers read it as blank. The new one is generated with real fonts and text runs, so keyword
matching works.

## Sending rules
1. One mail per company. **Never** CC/BCC across employers.
2. Batches of 8–10, Tue–Thu, 10:00–11:30 IST.
3. Attach only the CV (one file). Link the portfolio instead of attaching screenshots.
4. Follow up **once** after 4 working days, same thread.
5. Where a company also has a portal (Kratikal, Aujas, TAC, Amity, Bennett, Sharda), do both.
6. Verify each address on the company's own careers page at send time — HR inboxes change.

## Status (as of 23 Oct 2026)
- **31 mails sent on 23 Oct** — trainer/faculty roles across NCR colleges & institutes + security/VAPT roles
- **11 companies already applied to earlier** (Sep–Oct 2026) — deliberately not re-mailed
- Tracker: `applications.csv` (Status column), live at `/portfolio.html` → Applications

## Target mix (42)
- 30 training institutes / colleges / universities — trainer, faculty, SME roles
- 12 security consultancies / product firms — VAPT, AppSec, red-team roles

### Trainer / teaching targets sent on 23 Oct
CETPA (Noida) · NIIT (Gurugram) · Amity University (Noida) · Bennett University (Greater Noida) ·
Sharda University (Greater Noida) · Manav Rachna (Faridabad) · Jetking (Delhi) · Recon Cyber Security (Delhi) ·
Galgotias University (Greater Noida) · IIMT (Greater Noida) · GNIOT (Greater Noida) ·
Noida International University · Cyberyaan (Tilak Nagar) · Cryptus Cyber Security (Shakarpur) ·
K.R. Mangalam (Gurugram) · SGT University (Gurugram) · C-DAC Noida · NIELIT Delhi (Janakpuri) ·
Amity Gurugram · Amity Greater Noida · Appin Technology Lab (Delhi)

### Security / VAPT targets sent on 23 Oct
Certcube Labs · TAC Security · Sveltetech (Gurugram) · Innefu Labs · Torrid Networks (Noida) · CyberSRC (Noida) ·
CyberX Infosystem (Noida) · V Patrol AI (Gurugram) · CyberCube Services (Gurugram) · Antihak AI (Noida)

Locations covered: New Delhi (South Ex, Saket, Laxmi Nagar, Pitampura, Janakpuri, Burari,
Kalkaji, Aerocity, Netaji Subhash Place), Noida (Sectors 1, 2, 16, 62, 63, 68), Greater Noida,
Gurugram and Faridabad.
