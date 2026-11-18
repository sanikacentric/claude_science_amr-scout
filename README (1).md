# AMR Scout — Carbapenem Resistance in *Klebsiella pneumoniae* (Pilot)

An open-source pilot showing how a scientist can use **Claude Science** + **BioLit MCP** to explore antimicrobial resistance (AMR) in public pathogen data, with every key finding grounded in published literature.

> **Status:** 50-isolate pilot. See [Roadmap](#roadmap) for the full benchmark and workshop kit.

## Why this project
Before moving into AI engineering, I did microbiology research at the Haffkine Institute, Mumbai, and HIV/AIDS research at JJ Hospital, Mumbai. AMR is one of the WHO's top global health threats, and carbapenem-resistant *K. pneumoniae* is on the WHO **critical priority** pathogen list. This project asks what a bench scientist with no coding background can realistically do with Claude Science.

## Question
How common are the major carbapenemase genes (**KPC, NDM, OXA-48-like**) in a sample of public *K. pneumoniae* isolates, and how does their prevalence differ by country?

## Data
- **Source:** NCBI Pathogen Detection Isolates Browser (organism: *Klebsiella pneumoniae*)
- **Sample:** 50 isolates, downloaded on `YYYY-MM-DD`
- **Fields used:** isolate ID, country, collection year, isolation source, AMR genotypes (AMRFinderPlus calls from NCBI)
- Raw table: [`data/isolates.csv`](data/isolates.csv)

## Method
1. Load the isolate table in Claude Science
2. Parse AMR genotypes and flag carbapenemase genes (`blaKPC*`, `blaNDM*`, `blaOXA-48`-like)
3. Build a presence/absence table by isolate
4. Calculate prevalence by country and plot it
5. Use **BioLit MCP** to pull PubMed papers that support or contradict the top finding

Notebook: [`notebooks/amr_scout_pilot.ipynb`](notebooks/amr_scout_pilot.ipynb)

## Results
![Carbapenemase prevalence by country](figures/carbapenemase_by_country.png)

| Finding | Evidence (BioLit / PubMed) |
|---|---|
| 1. _e.g. KPC was the most common carbapenemase in the sample (X/50)_ | _PMID: …_ |
| 2. _e.g. NDM appeared mostly in isolates from …_ | _PMID: …_ |
| 3. _e.g. X% of isolates carried no carbapenemase_ | _PMID: …_ |

## Limitations
- 50 isolates is a **pilot**, not a representative sample: public databases over-represent some countries and outbreak investigations
- Genotype calls come from NCBI's AMRFinderPlus pipeline; we did not re-run gene detection
- Genotype ≠ phenotype: carrying a gene does not guarantee clinical resistance

## Where Claude Science helped and where it broke
Every session is logged in [`benchmark/benchmark_log.csv`](benchmark/benchmark_log.csv), including failures, errors and whether the reviewer agent caught them.

## Roadmap
- [ ] **Scale up:** 500+ isolates across all WHO priority pathogens, trends over time, CARD cross-check
- [ ] **HIV drug-resistance kit:** a no-code analysis using the Stanford HIV Drug Resistance Database
- [ ] **Benchmark:** reproduce 15–20 published infectious-disease analyses in Claude Science, score them, publish 5 product asks
- [ ] **Lab Starter Kit:** workshop slides, notebooks, facilitator guide and a 2-week adoption survey
- [ ] **Run one workshop** with grad students or at a local library

## Related
- [BioLit MCP](LINK): my open-source MCP server over PubMed for life sciences

## License
MIT
