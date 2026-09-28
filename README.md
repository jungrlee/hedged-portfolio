# Jung Ryul LeePortfolio

A portfolio construction project for a Korean (KRW-based) investor: a systematic stock screen and valuation across the US, Korea and Japan, a hedge sleeve built from ETFs, and a two-pass portfolio optimisation.

**Report:** [`report/Hedged_Multi-Asset_Portfolio.pdf`](report/Hedged_Multi-Asset_Portfolio.pdf) (also `.docx`) · **Notebook:** [`notebook/Portfolio_Screen_and_Optimization.ipynb`](notebook/Portfolio_Screen_and_Optimization.ipynb)

## Process

| Stage | US | Korea | Japan | Total |
|---|---|---|---|---|
| Universe (≈100 largest per market) | 108 | 92 | 100 | 300 |
| In scope (profitable, not a holding company) | 107 | 82 | 99 | 288 |
| Valued in full | 39 | 37 | 36 | 112 |
| ≥15% upside | 13 | 19 | 18 | 50 |
| Held | 3 | 12 | 4 | 19 |

1. **Screen**: forward earnings yield, FCF yield and ROE ÷ P/B, ranked within each market; top 30 per market plus names with earlier hand-built models.
2. **Value**: justified P/B for financials, mid-cycle justified P/B for cyclicals, and a 10-year earnings/FCF model for everything else. CAPM cost of equity per market.
3. **Select**: 60 max-Sharpe runs with noisy expected returns; keep stocks chosen in ≥50% of runs.
4. **Size**: max-Sharpe with a risk-parity penalty, an 11-factor covariance model (incl. USD/KRW and JPY/KRW) and mandate constraints (hedges ≥38%, sector caps, no market quotas).

Ex-ante (KRW): expected return 9.5%, volatility 5.3%, Sharpe 1.26 (benchmark 0.41). Equal weighting the same assets gives 1.22, so most of the value comes from selection.

## Stocks held

| Stock | Code | Market | Weight | Upside |
|---|---|---|---|---|
| AT&T | T | US | 2.00% | +40% |
| Cigna Group | CI | US | 1.75% | +55% |
| VICI Properties | VICI | US | 1.25% | +41% |
| Woori Financial Group | 316140 | KR | 2.00% | +69% |
| Korea Electric Power | 015760 | KR | 2.75% | +118% |
| KT&G | 033780 | KR | 2.75% | +28% |
| Industrial Bank of Korea | 024110 | KR | 2.25% | +101% |
| Hyundai Glovis | 086280 | KR | 1.50% | +43% |
| KT Corp | 030200 | KR | 2.50% | +61% |
| DB Insurance | 005830 | KR | 2.75% | +101% |
| Krafton | 259960 | KR | 2.50% | +98% |
| Coway | 021240 | KR | 2.50% | +80% |
| Hankook Tire & Technology | 161390 | KR | 2.50% | +61% |
| LG Uplus | 032640 | KR | 2.50% | +79% |
| JB Financial Group | 175330 | KR | 2.00% | +82% |
| MS&AD Insurance | 8725 | JP | 2.25% | +83% |
| ORIX | 8591 | JP | 2.00% | +55% |
| Sompo Holdings | 8630 | JP | 2.25% | +71% |
| Astellas Pharma | 4503 | JP | 2.25% | +54% |

The full list with ETFs is in `data/final_weights.csv`; all 50 hurdle-passing candidates are in `data/candidates.csv`.

## Reproduce

```bash
pip install -r requirements.txt
python src/1_parse_screen_data.py   # data/screen_raw.txt -> data/universe.json
python src/2_screen_and_value.py    # -> data/screen_results.json
python src/3_optimise.py            # -> data/results.json (a few minutes)
python src/4_optimizer_comparison.py
python src/5_charts.py              # -> images/
```

Run from the repository root. `data/bespoke_valuations.json` holds the hand-built valuations from the earlier version.

## Limitations

Correlations and factor loadings are assumptions anchored to history, not estimated from return data. Multiples come from one vendor on one date. The Korea-heavy result depends on the higher assumed Korean equity premium and on the absence of FX risk for a KRW investor.

*For discussion only. Not investment advice.*
