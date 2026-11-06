# v1 → v2 migration notes

v2 safety boundary ko intentionally tight karta hai. Purane workflows jo arbitrary shell ya exploit
frameworks par depend the, ab supported nahi hain.

## Retired / changed

- `SUPERAGENT_ALLOW_SHELL` / `SUPERAGENT_ALLOW_INSTALL`: ignored; raw shell aur remote install endpoints `410`.
- `POST /api/command/shell`, `POST /api/install`: retired.
- `auto_approve` chat flag: ignored; har live mission/adapter ko human approval chahiye.
- Query-string tokens (`?token=`): retired. `X-Agent-Token` header ya login cookie use karo.
- Public `scanme.nmap.org` demo RoE seed: retired. Offline fixture demo use karo.
- 139-tool catalog: reference map. Executable adapters sirf `dig`, `whois`, `nmap` (fixed safe ports).
- Provider status ab key hint return nahi karta.
- Live mode bina `APP_PASSWORD` / token ke start nahi hota.
- Default `HOST=127.0.0.1`, `SUPERAGENT_ALLOW_PRIVATE_RANGES=0`.

## New surfaces

- `POST /api/missions`, `GET /api/missions`, `GET /api/missions/{id}`, `POST /api/missions/{id}/cancel`
- `POST /api/demo/mission` (sirf `SUPERAGENT_DEMO_MODE=1`)
- `GET /api/provider`, `POST /api/provider/test`
- Mission reports/evidence automatically bante hain.

## Upgrade steps

1. Backup `data/superagent/` (especially `roe/ledger.jsonl`, audit, reports).
2. `.env` ko `superagent/.env.example` se compare karo; credentials/provider set karo.
3. `pip install -r superagent/requirements.txt`
4. Tests: `python -m pytest -q superagent/tests/test_v2.py && python -m superagent.tests.test_smoke`
5. `bash scripts/superagent.sh --demo` se UI verify karo, phir live mode.

Existing RoE ledger format compatible hai. Agar ledger corrupt hua to v2 fail-closed refuse karega;
backup se restore karo ya naya record banao. Purane running/approval states restart par `interrupted`
ho jate hain — naya mission plan banao.
