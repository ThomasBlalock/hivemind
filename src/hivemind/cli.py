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
