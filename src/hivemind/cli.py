"""hivemind CLI."""

from __future__ import annotations

import click

from hivemind.config import default_corpus_path, default_skills_src


@click.group()
def main() -> None:
    """HiveMind — Dynamic Context Optimization Hub."""


@main.group()
def corpus() -> None:
    """Corpus operations."""


@corpus.command("pull")
@click.option(
    "--sources",
    multiple=True,
    default=("anthropic_skills",),
    help="Source adapters to pull. Repeat the flag to pull multiple.",
)
@click.option(
    "--out",
    "out_dir",
    default=None,
    type=click.Path(),
    help="Directory to write skill markdown files into. Defaults to corpus/skills/.",
)
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Optional cap on skills per source (testing / bandwidth control).",
)
def corpus_pull(sources: tuple[str, ...], out_dir: str | None, limit: int | None) -> None:
    """Fetch external skill repos and write them as markdown files."""
    from pathlib import Path

    from hivemind.corpus.pull import pull_sources

    out_path = Path(out_dir) if out_dir else default_skills_src()
    written = pull_sources(list(sources), out_path, limit_per_source=limit)
    for name, paths in written.items():
        click.echo(f"  {name}: wrote {len(paths)} skill file(s) to {out_path}")
    click.echo(f"Total skills written: {sum(len(v) for v in written.values())}")
    click.echo("Next: run `hivemind corpus build` to ingest into skills.jsonl.")


@corpus.command("build")
@click.option("--src", "src_dir", default=None, type=click.Path(), help="Source markdown dir.")
@click.option("--out", "out_path", default=None, type=click.Path(), help="Output jsonl path.")
def corpus_build(src_dir: str | None, out_path: str | None) -> None:
    """Walk markdown files, audit, normalize, emit skills.jsonl."""
    from pathlib import Path

    from hivemind.corpus.ingest import ingest_directory, write_jsonl

    src = Path(src_dir) if src_dir else default_skills_src()
    out = Path(out_path) if out_path else default_corpus_path()
    skills = ingest_directory(src)
    n = write_jsonl(skills, out)
    statuses = {}
    for s in skills:
        statuses[s.audit_status] = statuses.get(s.audit_status, 0) + 1
    click.echo(f"Read {len(skills)} skills from {src}")
    for k, v in statuses.items():
        click.echo(f"  audit:{k} = {v}")
    click.echo(f"Wrote {n} skills (audit_status != 'failed') to {out}")


@main.command("serve")
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8000, type=int)
@click.option("--policy", default=None, help="Default policy. Overrides HIVEMIND_DEFAULT_POLICY.")
def serve(host: str, port: int, policy: str | None) -> None:
    """Run the FastAPI service."""
    import os

    import uvicorn

    if policy:
        os.environ["HIVEMIND_DEFAULT_POLICY"] = policy
    uvicorn.run("hivemind.api.app:app", host=host, port=port, log_level="info")


@main.group()
def dspy() -> None:
    """DSPy / System 2 operations."""


@dspy.command("train")
@click.option("--out-version", default="v1", help="Artifact version directory under models/dspy/.")
@click.option("--max-lm-calls", type=int, default=200, help="Hard cap on LM calls.")
@click.option("--dry-run", is_flag=True, help="Use dspy.DummyLM; no network calls.")
def dspy_train(out_version: str, max_lm_calls: int, dry_run: bool) -> None:
    """Compile DSPy artifacts (distillations, selector, order_prior)."""
    from hivemind.policies.dspy_train import main as train_main

    argv = ["--out-version", out_version, "--max-lm-calls", str(max_lm_calls)]
    if dry_run:
        argv.append("--dry-run")
    rc = train_main(argv)
    if rc != 0:
        raise SystemExit(rc)


@main.command("policies")
def policies_cmd() -> None:
    """List registered policies."""
    # Import for side-effect registration.
    import hivemind.policies.baseline  # noqa: F401
    import hivemind.policies.dspy_compiled  # noqa: F401
    import hivemind.policies.hybrid_retrieval  # noqa: F401
    import hivemind.policies.online_bandit  # noqa: F401
    from hivemind.policies import list_policies

    for n in list_policies():
        click.echo(n)


if __name__ == "__main__":  # pragma: no cover
    main()
