# CVPR 2024 Scraper Run Failure Summary

## What happened

The repository contains a sample output file for five CVPR 2024 papers, but the current execution environment could not complete a live run of the scraper against the CVPR OpenAccess website for all papers.

The attempted full-run command was:

```bash
python3 3.1_cvpr_conf_extract/src/scrape_cvpr2024.py --format json --output 3.1_cvpr_conf_extract/results/cvpr2024_papers.json
```

That command failed before it could fetch any listing page, so `3.1_cvpr_conf_extract/results/cvpr2024_papers.json` could not be generated in this container.

## Why the five-paper result and all-paper run looked inconsistent

The five-paper sample file existing in `results` does not prove that the scraper successfully fetched those five papers live in this same environment. With the current scraper implementation, both the five-paper command and the all-paper command must first download the CVPR listing page or pages. The `--limit 5` option only limits how many parsed paper detail pages are processed after the listing pages are fetched.

Therefore, if the environment cannot reach `openaccess.thecvf.com`, a live five-paper run and a live all-paper run should both fail at the initial listing-page fetch step.

The most likely explanation is that the five-paper JSON was produced earlier under different network conditions, from another source, or manually, while the later all-paper run was attempted in a container that could not access the target website.

## Network errors observed

Two access paths were tested:

1. Using the configured HTTP(S) proxy failed with:

   ```text
   Tunnel connection failed: 403 Forbidden
   ```

2. Clearing the proxy environment variables failed with:

   ```text
   Temporary failure in name resolution
   ```

These errors indicate an environment/network restriction, not a scraper parsing error.

## Key takeaway

The all-paper scrape failed because the container could not reach the CVPR OpenAccess website. The apparent success of the five-paper result should be treated as a pre-existing sample artifact, not evidence that live website access works from this environment.
