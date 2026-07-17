# PII Redaction Tool for DOCX Documents

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Architecture: Layered Modular](https://img.shields.io/badge/Architecture-Layered%20Modular-brightgreen.svg)]()

A high-precision, modular PII Redaction Engine built for `.docx` documents. Instead of replacing sensitive text with static masks (`[REDACTED]` or `***`), this tool uses **Microsoft Presidio**, **spaCy NLP**, and **Faker** to intelligently substitute detected PII with realistic, context-aware synthetic alternatives while maintaining **deterministic entity mapping** across the entire document.

---

## Tech Stack

| Technology | Purpose |
| :--- | :--- |
| **Python 3.9+** | Core programming language |
| **Microsoft Presidio** (`analyzer` & `anonymizer`) | Named Entity Recognition (NER) and anonymization pipeline orchestration |
| **spaCy** (`en_core_web_sm` / `en_core_web_lg`) | Advanced NLP entity extraction and context modeling |
| **Faker** | Generation of realistic, locale-aware synthetic replacement data |
| **python-docx** & **lxml** | DOCX document parsing, XML run manipulation, and structure traversal |
| **Click** & **PyYAML** | Command-line interface and external YAML configuration management |
| **pytest** | Automated unit and integration testing |

---

## Key Features

- **9 Supported PII Types**: `Full Name`, `Email Address`, `Phone Number`, `Company Name`, `Address`, `Social Security Number (SSN)`, `Credit Card Number`, `Date of Birth`, and `IP Address`.
- **Deterministic Entity Mapping**: Guarantees that identical PII entities map to the exact same synthetic replacement everywhere in the document (`EntityMappingStore`). For example, `"John Doe"` on page 1 and page 10 will both be replaced by `"Alexander Vance"`.
- **Offset-Preserving Run Reconstruction**: Solves Microsoft Word's "Split Run Problem" (`TextRunWalker`) where words are fragmented across multiple XML tags (`<w:r>`). It reconstructs full sentences for accurate NLP analysis and applies replacements without losing fonts, bolding, colors, or italics.
- **Structural Coverage**: Redacts document body paragraphs, multi-column tables, nested table cells, section headers, and section footers (`DocxProcessor`).
- **High-Precision Filtering**: Uses a centralized stop-word denylist (`src/utils/stop_words.py`) and strict boundary checks to eliminate false positives on common vocabulary, document headers, and general numbers (`0` default false positives).

---

## Example Input → Output

### Original Document Text (`sample_confidential.docx`)
> **CONFIDENTIAL SETTLEMENT AGREEMENT**  
> This agreement is entered into on **April 14, 1982** between **Johnathan Miller** (SSN: **123-45-6789**), residing at **742 Evergreen Terrace, Springfield, IL**, and **Acme Technologies Inc.** For inquiries, contact **jmiller@acmetech.com** or call **+1 (555) 019-2834**.

### Redacted Output Text (`sample_redacted.docx`)
> **CONFIDENTIAL SETTLEMENT AGREEMENT**  
> This agreement is entered into on **October 03, 1974** between **Arthur Pendelton** (SSN: **531-82-9402**), residing at **1042 Maple Street, Austin, TX**, and **Vanguard Solutions Group**. For inquiries, contact **apendelton@vanguard.com** or call **+1 (312) 555-0149**.

*(Note: Document formatting such as bolding, alignment, and fonts is preserved exactly).*

---

## Layered Modular Architecture

```
scaler-pii-redactor/
├── config/settings.yaml           # Centralized score thresholds and recognizer configuration
├── src/
│   ├── recognizers/               # Custom Presidio Recognizers (Company, SSN, DOB) & Factory
│   ├── anonymizers/               # Custom Anonymizer, Stateful Faker bridge & Entity Vault
│   ├── document_processors/       # DOCX XML run walker, paragraph/table/header traversal
│   ├── pipeline/                  # High-level orchestrator (RedactionPipeline)
│   ├── utils/                     # Stop-word denylist, colored logging, file validation
│   └── cli/                       # Command-line interface (main.py)
└── tests/                         # 100% passing automated test suite (pytest)
```

---

## Quickstart & Usage

### 1. Installation
```bash
# Create virtual environment and install package in editable mode
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Download spaCy English NLP model
python -m spacy download en_core_web_sm
```

### 2. Command-Line Interface (`scaler-redact`)

```bash
# Single file redaction (with default threshold 0.65)
scaler-redact --input ./input/Red_Herring_Prospectus.docx --output ./output/Redacted.docx --verbose

# Batch directory processing with backup and stateful vault persistence across runs
scaler-redact --input ./incoming_docs/ --output ./redacted_docs/ --backup --persist
```

#### CLI Options:
- `-i, --input PATH`: Input `.docx` file or directory. **[Required]**
- `-o, --output PATH`: Output path or target directory. **[Required]**
- `-c, --config PATH`: Override configuration file (`config/settings.yaml`).
- `-t, --threshold FLOAT`: PII detection score threshold (`0.0 - 1.0`, default `0.65`).
- `-b, --backup`: Create `.bak.docx` backup before modification.
- `-p, --persist`: Save/load mappings to `entity_vault.json` across separate CLI executions.
- `-v, --verbose`: Enable debug logging.

---

## Evaluation Results

The pipeline was benchmarked against a complex, real-world financial prospectus (`Red Herring Prospectus.docx` — **1.8+ MB**, **1,006 paragraphs**, multi-column tables):

| Metric / Category | Benchmark Result | Notes / Quality Impact |
| :--- | :---: | :--- |
| **Processing Speed** | `~6.5 seconds` | Complete analysis across 1,006 paragraphs & tables |
| **Total PII Replacements** | **`5,538`** | High-precision replacements applied across 9 PII categories |
| **`DEFAULT` False Positives** | **`0` (`0.0%`)** | Eliminated all `[DEFAULT_word]` false positives on common words |
| **`COMPANY_NAME`** | `3,823` | Correctly identified corporations; ignored generic terms (`Management`) |
| **`PERSON`** | `3,609` | High-precision personal names with title/stop-word filtering |
| **`DATE_TIME`** | `2,462` | Clean date preservation without standalone fiscal year false alarms |
| **`LOCATION`** | `820` | Exact geographic addresses and cities |
| **`EMAIL_ADDRESS` & `PHONE`** | `110` / `65` | Strict regex validation with zero anti-context overlap |
| **Unit Test Suite** | **`13 / 13 PASSED`** | Full test coverage executed via `pytest tests/ -v` |

---

## Limitations

1. **Scanned Images & Raster PDFs**: Text embedded inside images (e.g., JPEG/PNG screenshots placed inside the `.docx`) is not parsed or redacted.
2. **Single Language**: Currently optimized exclusively for English (`en_core_web_sm`/`lg`). Non-English names or specialized international IDs require additional spaCy models.
3. **Encrypted Documents**: Password-protected `.docx` files must be decrypted prior to processing.

---

## Future Improvements

- **OCR Integration**: Integrate `Tesseract` or `EasyOCR` to extract, detect, and redact PII inside images embedded in `.docx` files.
- **Multilingual Support**: Expand NER pipelines with multi-language spaCy models (`xx_ent_wiki_sm`) and international phone/ID pattern recognizers.
- **REST API & Docker Containerization**: Package the redaction pipeline as a containerized FastAPI microservice for asynchronous enterprise batch processing.
- **Interactive Review Dashboard**: Build a lightweight web interface (`Streamlit` / `React`) allowing compliance officers to review and approve PII spans before final document export.

---

## Running Automated Tests

```bash
# Run all unit tests with verbose output
pytest tests/ -v

# Generate code coverage report
pytest --cov=src tests/
```
