Put your own files here and the dashboard uses them instead of the bundled examples.

  input/scored_runs.csv   (or scored_runs.json)   the file written by the scoring engine
  input/calibration/      the "results" folder from the calibration and validation package

Anything not found here falls back to the matching file in ../examples/.
Then run:  streamlit run streamlit_app.py   (or: py dashboard.py)
