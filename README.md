# NEXUS for 73 Strings

An independent portfolio case study by Firman Insan Muhammad (VIM), prepared for the Senior Data Engineer role at 73 Strings in London.

Live site: https://rfim.github.io/nexus-73strings/

The role-specific architecture is based on the job description supplied by the portfolio owner. 73 Strings describes its product focus as [data extraction, portfolio monitoring and valuations](https://www.73strings.com/). The Lifepal and Deloitte experience and outcomes on the site come from VIM's CV and cover letter. The site is neither affiliated with nor endorsed by 73 Strings.

The case study shows how reusable feed metadata supports extraction, freshness and reconciliation protect monitoring, and versioned lineage makes valuation inputs explainable. These are practical uses of the engineering patterns VIM built at Lifepal, shown against the 73 Strings role. The site does not claim they are deployed at 73 Strings.

The `examples/` directory is a separate synthetic reference. It demonstrates source-LSN ordering, deletes, replay, conflicting-LSN quarantine, row-level validation, reconciliation, metadata-driven feed mapping, SCD2 history and tenant-scoped delivery. It does not connect to 73 Strings, Lifepal, Azure, Snowflake or SQL Server. The Databricks SQL files are illustrative sketches, while `.github/workflows/ci.yml` is a real GitHub Actions workflow.

Run the local checks with Python 3.12 or newer:

```sh
python3 -m unittest discover -s examples -p 'test_*.py' -v
```

After changing example source files, regenerate the source-backed website excerpts:

```sh
python3 scripts/build_snippets.py
```

The technology icons are vendored from [Devicon](https://github.com/devicons/devicon), [Simple Icons](https://github.com/simple-icons/simple-icons), and the [Delta Lake website](https://github.com/delta-io/website). License and notice files are in `assets/`. Technology marks identify tools and do not imply endorsement. The Roojai/Lifepal image was provided by the portfolio owner in a previous iteration of this case study.
