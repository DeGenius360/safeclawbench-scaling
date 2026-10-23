# Publishing checklist

Suggested repo name: **`safeclawbench-qwen-scaling`**

## Before the first push — fill in / decide

- [ ] Replace `<YOUR NAME>` in `LICENSE` and the `<YOUR ...>` fields in `CITATION.cff`.
- [ ] Set the real repo + Pages URLs in `CITATION.cff` and anywhere the README links to Pages.
- [ ] Decide whether to publish `kit/` (the generation/judging scripts). See `kit/README.md`.

## Secrets check (do not skip)

- [ ] No `keys.env`, `.env`, `*.key`, service-account JSON, or notebook output cells with tokens.
- [ ] No API keys in `kit/` scripts, cloudflared config, or any committed log.
- [ ] **Revoke the exposed Gemini key and delete the expired Anthropic key** before anything goes
      public (these were used during generation).
- [ ] Run a scan, e.g. `gitleaks detect --source .` or
      `git grep -nE '(sk-[A-Za-z0-9]{20}|AIza[0-9A-Za-z_-]{30}|BEGIN [A-Z ]*PRIVATE KEY)'`.
- [ ] Add a `.gitignore` for `*.env`, `*.key`, `__pycache__/`, `out/`, `*.ipynb_checkpoints`.

## Do NOT commit (licence / safety)

- [ ] `benchmark_v5_600.json` and the raw attack prompts — link to the
      [Hugging Face dataset](https://huggingface.co/datasets/sairights/safeclawbench); confirm its
      licence allows your use and check whether it asks you not to redistribute scenarios.
- [ ] Raw model responses / full transcripts (the released CSVs carry verdicts and metrics only).
- [ ] The blind adjudication sheet and answer key — they contain full prompts and responses; keep
      those private.

## GitHub Pages

1. Push the repo to GitHub (public).
2. **Settings → Pages →** Source: *Deploy from a branch*; Branch: `main`, folder `/ (root)`.
3. Add a one-line redirect or move `report/index.html` to the repo root as `index.html` if you want
   the report served at the bare Pages URL. (Keeping it in `report/` serves it at
   `https://<user>.github.io/safeclawbench-qwen-scaling/report/`.)
4. The report is fully static and offline-capable; the only external request is Google Fonts, which
   degrades gracefully to system fonts if blocked.
5. Confirm the `<picture>` dark/light figures render on both GitHub themes.

## Nice-to-have

- [ ] A short `data/README.md` describing the CSV columns.
- [ ] Tag a release `v1.0.0` so `CITATION.cff` resolves to a fixed version.
- [ ] Topic tags on the repo: `agent-security`, `prompt-injection`, `llm-evaluation`, `qwen`.
