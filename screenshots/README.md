# Screenshots

No screenshots are committed yet. To add them:

1. Run the app locally: `uvicorn backend.app.main:app --reload`
2. Capture these views at ~1280px width (browser dev tools → device toolbar):
   - `home.png` — the landing page (`#/`)
   - `categories.png` — category list with a search in progress (`#/categories`)
   - `item-detail.png` — a reference item (`#/item/ref-001`)
   - `practice-case.png` — a case with two steps revealed (`#/case/case-001`)
   - `training.png` — the training modules page (`#/training`)
   - `quiz-results.png` — the quiz after "Check answers" with a mixed score
3. Save them in this folder with the names above, then embed the best 2–3 in
   the main README:

   ```markdown
   ![Quiz results](screenshots/quiz-results.png)
   ```

Tip: an animated GIF of the practice-case reveal flow (e.g. via LICEcap or
Kap) is worth more than any static screenshot on a GitHub README.
