# Draft Agent

Outline, grouping, hero photo, and photo summary artifacts are converted into a first-pass Korean blog draft.

## Run

```bash
pip install -r requirements.txt
uvicorn src.api_server:app --reload --port 8400
```

## Verify

```bash
scripts/verify.sh
```
