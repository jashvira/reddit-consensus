# Reddit Evaluation Dataset Pipeline

**EXPERIMENTAL CODE**
This directory contains research/experimental code for generating evaluation questions from Reddit discussions. The code is not production-ready and may contain hardcoded paths, incomplete error handling, and other research-quality shortcuts.

This directory contains tools and datasets for generating evaluation questions from Reddit discussions using a cost-optimized 3-pass pipeline.

## Quick Start

```bash
# Screen posts only (fast, cheap)
python scripts/question_curator.py --screen-only --max-posts 100

# Generate masked questions (default mode)
python scripts/question_curator.py --max-posts 50

# Generate direct questions (no masking, 30% cheaper)
python scripts/question_curator.py --max-posts 50 --no-masking
```

## Dataset Acquisition

The pipeline uses historical Reddit data from February 2016. The raw datasets (~9.9GB) are excluded from git but can be downloaded:

```bash
# Create datasets directory
mkdir -p evals/datasets

# Download Reddit comments (February 2016) - 8.9GB
wget https://huggingface.co/datasets/fddemarco/pushshift-reddit-comments/resolve/main/RC_2016-02.parquet -P evals/datasets/

# Download Reddit submissions (February 2016) - 1.1GB
wget https://huggingface.co/datasets/fddemarco/pushshift-reddit/resolve/main/RS_2016-02_00.parquet -P evals/datasets/
```

**Alternative using datasets library:**
```python
from datasets import load_dataset

# Load comments
comments = load_dataset("fddemarco/pushshift-reddit-comments",
                       data_files="RC_2016-02.parquet")

# Load submissions
posts = load_dataset("fddemarco/pushshift-reddit",
                     data_files="RS_2016-02_00.parquet")
```

## Pipeline Overview

### 3-Pass Question Generation (Default)
1. **Content Screening** (`gpt-4o-mini`, ~$0.0001) - Accept/reject posts
2. **Keyword Extraction** (`gpt-4o-mini`, ~$0.0001) - Build forbidden word list
3. **Masked Question Generation** (`gpt-4o`, ~$0.01) - Create abstract questions

### 2-Pass Direct Questions (`--no-masking`)
1. **Content Screening** (`gpt-4o-mini`, ~$0.0001) - Accept/reject posts
2. **Direct Question Generation** (`gpt-4o`, ~$0.007) - Use original terminology

## File Structure

```
evals/
├── scripts/
│   ├── question_curator.py      # Main 3-pass question generation
│   ├── process_reddit_data.py   # Data filtering pipeline
│   └── list_ask_subreddits.py   # Subreddit discovery
├── datasets/                    # Raw Reddit data (excluded from git)
│   ├── RC_2016-02.parquet      # Comments (8.9GB)
│   └── RS_2016-02_00.parquet   # Submissions (1.1GB)
├── processed/                   # Filtered datasets (included)
│   ├── reddit_2016_filtered_2.parquet  # 816 high-quality posts
│   └── curated_questions_2.json        # Generated questions
├── notebooks/                   # Data exploration
└── results/                     # Analysis outputs
```

## Command Line Options

```bash
python scripts/question_curator.py [OPTIONS]

Options:
  --input PATH              Input parquet file
  --output PATH             Output JSON file
  --max-concurrent INT      Concurrent requests (default: 5)
  --start-idx INT           Start index (default: 0)
  --max-posts INT           Max posts to process
  --screen-only             Only run screening, no question generation
  --no-masking              Skip keyword extraction, allow direct questions
  --max-retries INT         Max retries for rate limits (default: 3)
```

## Output Format

### Masked Questions (Default)
```json
{
  "source_post_id": "47qa3h",
  "subreddit": "AskUK",
  "original_title": "Why do British judges wear those oldtimey white wigs?",
  "original_body": "Watching Broadchurch on Netflix...",
  "accepted": true,
  "questions": [
    "What traditional attire functions as a symbol to emphasize formal legal proceedings?",
    "In what situations is this traditional dress often omitted?"
  ],
  "forbidden_keywords": ["British judges", "lawyers", "wigs", "courtroom"],
  "key_comment_ids": ["d0etxn6", "d0euftf"],
  "masking_mode": true,
  "metrics": {
    "total_cost": 0.0004425,
    "total_tokens": 2317,
    "total_retries": 0,
    "passes_used": 3
  }
}
```

### Direct Questions (`--no-masking`)
```json
{
  "masking_mode": false,
  "forbidden_keywords": null,
  "questions": [
    "Why do British judges and lawyers wear those white wigs in court?",
    "When do UK courts not require the traditional judicial wigs?"
  ],
  "metrics": {
    "passes_used": 2,
    "total_cost": 0.0003015
  }
}
```

## Cost Analysis

| Mode | Passes | Cost per Question | Use Case |
|------|--------|------------------|----------|
| Masked | 3 | ~$0.01 | Abstract reasoning, concept understanding |
| Direct | 2 | ~$0.007 | Specific knowledge, factual recall |
| Screen Only | 1 | ~$0.0001 | Quality filtering |

## Key Features

- **Cost-optimized**: Cheap model for screening/extraction, quality model for generation
- **Rate limit handling**: Intelligent retry with exponential backoff
- **Progress tracking**: Real-time tqdm progress bars
- **Two evaluation modes**: Masked (abstract) vs Direct (specific) questions
- **Quality filtering**: Rejects subjective/unsuitable content
- **Structured output**: Clean JSON with metrics and traceability

## Dependencies

```bash
# Install with uv
uv sync --group eval

# Or with pip
pip install pandas numpy pyarrow datasets openai tqdm
```

## Performance Tips

- **Start small**: Use `--max-posts 10` for testing
- **Use screening**: Run `--screen-only` first to estimate accept/reject rates
- **Adjust concurrency**: Lower `--max-concurrent` if hitting rate limits
- **No-masking mode**: 30% cheaper and 33% faster for direct questions