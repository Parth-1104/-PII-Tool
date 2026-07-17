import logging
import sys
from pathlib import Path
from typing import Optional
import click
from src.pipeline.redactor_pipeline import RedactionPipeline
from src.utils.logger import setup_logging, get_logger

logger = get_logger("CLI")


@click.command(name="scaler-redact")
@click.option(
    "--input",
    "-i",
    "input_path",
    required=True,
    type=click.Path(exists=True),
    help="Path to input .docx document or directory containing .docx files.",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    required=True,
    type=click.Path(),
    help="Path to save redacted .docx document or destination directory for batch processing.",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    default=None,
    type=click.Path(exists=True),
    help="Optional path to custom configuration YAML (e.g. config/settings.yaml).",
)
@click.option(
    "--threshold",
    "-t",
    default=0.65,
    type=float,
    show_default=True,
    help="Minimum Presidio confidence score threshold for PII redaction [0.0 - 1.0].",
)
@click.option(
    "--backup",
    "-b",
    is_flag=True,
    default=False,
    help="Create a backup (.bak.docx) of the input file before redaction.",
)
@click.option(
    "--persist",
    "-p",
    is_flag=True,
    default=False,
    help="Enable stateful entity vault persistence to entity_vault.json across multiple runs.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose DEBUG logging.",
)
def cli(
    input_path: str,
    output_path: str,
    config_path: Optional[str],
    threshold: float,
    backup: bool,
    persist: bool,
    verbose: bool,
) -> None:
    """
    Industrial-Quality PII Redaction Tool for DOCX documents.
    Replaces sensitive personal data (Full Name, Email, Phone, Company, Address, SSN, DOB, IP, Credit Card)
    with realistic synthetic alternatives while guaranteeing deterministic entity consistency.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level=log_level)

    inp = Path(input_path).resolve()
    out = Path(output_path).resolve()

    # Initialize redaction pipeline
    try:
        pipeline = RedactionPipeline(
            config_path=config_path,
            score_threshold=threshold,
            enable_persistence=persist,
            persistence_path="./entity_vault.json" if persist else None,
        )
    except Exception as e:
        logger.critical(f"Failed to initialize redaction pipeline: {e}")
        sys.exit(1)

    # Handle batch directory vs single file
    if inp.is_dir():
        if out.exists() and out.is_file():
            logger.error("When input is a directory, output must also be a directory path.")
            sys.exit(1)
        out.mkdir(parents=True, exist_ok=True)

        docx_files = list(inp.glob("*.docx"))
        if not docx_files:
            logger.warning(f"No .docx files found inside directory: {inp}")
            sys.exit(0)

        logger.info(f"Starting batch redaction on {len(docx_files)} files in '{inp.name}'...")
        total_batch_replacements = 0

        for doc_file in docx_files:
            if doc_file.name.startswith("~$") or doc_file.name.endswith(".bak.docx"):
                continue
            target_out = out / f"{doc_file.stem}_redacted.docx"
            try:
                summary = pipeline.redact_document(doc_file, target_out, create_backup=backup)
                total_batch_replacements += summary["total_replacements"]
            except Exception as err:
                logger.error(f"Error processing {doc_file.name}: {err}")

        logger.info(f"Batch processing complete. Total replacements applied across batch: {total_batch_replacements}")

    else:
        # Single file mode
        if out.is_dir():
            out = out / f"{inp.stem}_redacted.docx"
        elif out.suffix.lower() != ".docx":
            out = out.with_suffix(".docx")

        try:
            summary = pipeline.redact_document(inp, out, create_backup=backup)
            click.echo("\n" + "=" * 60)
            click.echo("           REDACTION AUDIT SUMMARY REPORT")
            click.echo("=" * 60)
            click.echo(f"Input File          : {summary['input_file']}")
            click.echo(f"Output File         : {summary['output_file']}")
            click.echo(f"Paragraphs Scanned  : {summary['paragraphs_processed']}")
            click.echo(f"Total Replacements  : {summary['total_replacements']}")
            click.echo("-" * 60)
            click.echo("Replacements by PII Type:")
            for pii_type, count in summary["entity_counts"].items():
                click.echo(f"  * {pii_type:<18}: {count:>4}")
            if not summary["entity_counts"]:
                click.echo("  * No PII entities detected above confidence threshold.")
            click.echo("=" * 60 + "\n")
        except Exception as err:
            logger.critical(f"Redaction failed: {err}")
            sys.exit(1)


if __name__ == "__main__":
    cli()
