
# AI Development Log

## Project: Bitcoin Market Behaviour Analyzer

This log documents how AI assisted with development. AI-generated suggestions were reviewed and tested rather than accepted blindly.

### Prompt 1 — Project planning
**Prompt:** Help me plan a free Python project to analyse Bitcoin market behaviour using Kraken's public OHLC API.

**AI contribution:** Suggested a project structure, analysis metrics, and a staged implementation plan.

**My review/change:** I chose a staged approach, free tools, and local execution first. I did not approve paid services or hosting.

### Prompt 2 — Kraken API data collection
**Prompt:** Help me fetch and validate Bitcoin daily OHLC data from Kraken.

**AI contribution:** Suggested API error handling, numeric conversion, timestamp processing, and incomplete-candle exclusion.

**My review/change:** I tested the API response, including an invalid trading-pair scenario, and checked that errors were handled.

### Prompt 3 — Market metrics
**Prompt:** Help me calculate Bitcoin daily returns, 7-day and 30-day moving averages, unusual price movements, and high-volume days.

**AI contribution:** Suggested pandas calculations and rules for identifying unusual movements and high volume.

**My review/change:** I inspected the calculated values and added automated tests for selected analysis rules. I still need to document a manual calculation check against raw market data.

### Prompt 4 — Interactive dashboard
**Prompt:** Help me build a Streamlit dashboard with interactive Bitcoin charts and summary metrics.

**AI contribution:** Suggested a dashboard using Streamlit and Plotly, including price, volume, and daily-return charts.

**My review/change:** I ran the dashboard locally in a browser and confirmed that it opened and displayed the charts.

### Prompt 5 — Testing and project quality
**Prompt:** Help me test the market-analysis functions and prepare the project for GitHub.

**AI contribution:** Suggested pytest tests, dependency documentation, and Git ignore rules.

**My review/change:** I ran the automated tests and confirmed that all six tests passed. I created `.gitignore` and `requirements.txt`.

## Limitations and lessons learned

- AI-generated code can contain formatting or analytical mistakes, so outputs need to be checked.
- A successful run does not prove that every calculation is correct.
- Automated tests cover selected cases, not every possible API response or market condition.
- I independently checked the daily return for 26 October 2026 using the closing prices for 25 and 26 October. The calculation produced approximately -0.058215%, matching the Python output.


## Final verification status

- [x] Main Python script runs successfully.
- [x] Local dashboard opens.
- [x] Six automated tests pass.
- [x] `.gitignore` created.
- [x] `requirements.txt` created.
- [x] Manual calculation independently verified and documented.
- [ ] README and sample report reviewed.
- [ ] Final repository contents and GitHub link verified.
- [ ] All required files committed and pushed.