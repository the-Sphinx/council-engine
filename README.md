To start using it

  # 1. Download Quran corpus
  python scripts/download_quran.py

  # 2. Start the server (requires Ollama running)
  uvicorn app.main:app --reload

  # 3. Visit http://localhost:8000 → create project → upload corpus → build index → ask questions

  # 4. Run eval (after indexing)
  python scripts/run_eval.py --project-id <uuid> --eval-dataset data/evals/quran_eval_v1.json
  --label baseline_v1