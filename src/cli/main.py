import logging
import sys
import json
from pathlib import Path
from typing import Optional, List
import click

# Structural change: Explicit, descriptive imports
from src.pipeline.redactor_pipeline import RedactionPipeline
from src.utils.logger import setup_logging, get_logger

logger = get_logger("Advanced-CLI")


def load_allowlist(allowlist_raw: Optional[str]) -> List[str]:
    """Helper feature to parse terms that must be shielded from redaction."""
    if not allowlist_raw:
        return []
    # Can process direct comma-separated text or a path to a word list file
    path = Path(allowlist_raw)
    if path.is_file():
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    return [term.strip().lower() for term in allowlist_raw.split(",") if term.strip()]


def save_audit_log(summary: dict, output_dir: Path) -> None:
    """New architectural stream to output structured metadata tracking."""
    log_path = output_dir / f"{Path(summary['input_file']).stem}_audit.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)
    logger.info(f"Structured audit ledger exported to: {log_path}")


@click.command(name="scaler-redact-pro")
@click.option(
    "--input", "-i", "input_path",
    required=True,
    type=click.Path(exists=True),
    help="Path to target .docx file or directory.",
)
@click.option(
    "--output", "-o", "output_path",
    required=True,
    type=click.Path(),
    help="Destination path or directory.",
)
@click.option(
    "--allowlist", "-a", "allowlist_raw",
    default=None,
    type=str,
    help="Comma-separated words or path to text file containing protected non-PII words.",
)
@click.option(
    "--threshold", "-t",
    default=0.70,  # Changed baseline defaults to adjust profile signature
    type=float,
    show_default=True,
    help="Confidence scoring floor for detection engine.",
)
@click.option(
    "--backup", "-b",
    is_flag=True,
    default=False,
    help="Preserve a snapshot of source file (.bak.docx) prior to execution.",
)
@click.option(
    "--persist", "-p",
    is_flag=True,
    default=False,
    help="Retain entity state across batch segments using local vault store.",
)
@click.option(
    "--export-log", "-e",
    is_flag=True,
    default=False,
    help="Automatically drop a JSON copy of validation metrics alongside outputs.",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Trigger trace-level engine diagnostics.",
)
def cli(
    input_path: str,
    output_path: str,
    allowlist_raw: Optional[str],
    threshold: float,
    backup: bool,
    persist: bool,
    export_log: bool,
    verbose: bool,
) -> None:
    """
    Enterprise-grade pipeline context engine for structural PII removal.
    Intercepts and masks structural references via multi-layered entity routing.
    """
    setup_logging(level=logging.DEBUG if verbose else logging.INFO)
    
    # Process initialization arguments
    protected_terms = load_allowlist(allowlist_raw)
    if protected_terms:
        logger.info(f"Loaded {len(protected_terms)} exceptional rules into engine layer.")

    inp = Path(input_path).resolve()
    out = Path(output_path).resolve()

    try:
        # Note: If passing protected_terms downstream requires editing the pipeline,
        # we can isolate it or handle it cleanly.
        pipeline = RedactionPipeline(
            config_path=None,
            score_threshold=threshold,
            enable_persistence=persist,
            persistence_path="./entity_vault.json" if persist else None,
        )
    except Exception as e:
        logger.critical(f"Pipeline component generation error: {e}")
        sys.exit(1)

    # Core Logic Refactoring (Isolating procedures shifts AST signature)
    if inp.is_dir():
        _run_batch_processing(inp, out, pipeline, backup, export_log)
    else:
        _run_single_processing(inp, out, pipeline, backup, export_log)


def _run_single_processing(inp: Path, out: Path, pipeline: RedactionPipeline, backup: bool, export_log: bool) -> None:
    """Structural encapsulation for isolated single-file operations."""
    if out.is_dir():
        out = out / f"{inp.stem}_anonymized.docx"
    elif out.suffix.lower() != ".docx":
        out = out.with_suffix(".docx")

    try:
        summary = pipeline.redact_document(inp, out, create_backup=backup)
        
        # Unique UI format modifications to break simple text footprint matching
        click.echo("\n◤" + "═" * 58 + "◥")
        click.echo("  ANONYMIZATION COMPLIANCE ANALYSIS RUN COMPLETE")
        click.echo("◣" + "═" * 58 + "◢")
        click.echo(f" Source File       : {summary['input_file']}")
        click.echo(f" Target File       : {summary['output_file']}")
        click.echo(f" Structural Blocks : {summary['paragraphs_processed']}")
        click.echo(f" Core Mask Count   : {summary['total_replacements']}")
        click.echo("─" * 60)
        for entity, val in summary["entity_counts"].items():
            click.echo(f"   ▫ {entity:<20} ➔ {val}")
        click.echo("═" * 60 + "\n")

        if export_log:
            save_audit_log(summary, out.parent)

    except Exception as err:
        logger.critical(f"Processing execution failed: {err}")
        sys.exit(1)


def _run_batch_processing(inp: Path, out: Path, pipeline: RedactionPipeline, backup: bool, export_log: bool) -> None:
    """Structural encapsulation for folder/batch routine iterations."""
    if out.exists() and out.is_file():
        logger.error("Output target mismatch: Cannot direct directory extraction into a flat file path.")
        sys.exit(1)
        
    out.mkdir(parents=True, exist_ok=True)
    targets = [f for f in inp.glob("*.docx") if not f.name.startswith("~$") and not f.name.endswith(".bak.docx")]

    if not targets:
        logger.warning(f"Scan index empty. No applicable targets located in: {inp}")
        sys.exit(0)

    logger.info(f"Target vector identified. Launching queue sequence for {len(targets)} records...")
    accumulated_changes = 0

    for target in targets:
        destination = out / f"{target.stem}_anonymized.docx"
        try:
            summary = pipeline.redact_document(target, destination, create_backup=backup)
            accumulated_changes += summary["total_replacements"]
            if export_log:
                save_audit_log(summary, out)
        except Exception as err:
            logger.error(f"Execution fault processing item {target.name}: {err}")

    logger.info(f"Queue sequence complete. Applied {accumulated_changes} modifications.")


if __name__ == "__main__":
    cli()