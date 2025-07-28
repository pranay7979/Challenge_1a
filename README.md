# 🧠 Round 1A Submission - PDF Outline Extractor

## 📄 Challenge: Understand Your Document

This project is a solution to **Round 1A of the Adobe Hackathon 2024**, focused on extracting structured outlines from PDF documents using CPU-only, offline-compatible Python code. The tool is designed to extract:

- The **document title**
- Headings at hierarchy levels:
  - `H1` – Top-level sections
  - `H2` – Subsections
  - `H3` – Sub-subsections

The output is a structured JSON file with all valid headings per page, usable in downstream tasks like summarization, recommendation, and document understanding.

---

## ⚙️ Methodology

Our pipeline follows a carefully designed, rule-based approach using `pdfminer.six`, which avoids any model over 200MB and supports full offline inference.

### 1. **Text Block Extraction**

We use `pdfminer.high_level.extract_pages` to iterate over each page and extract layout elements. For each `LTTextContainer`, we parse individual lines (`LTChar`) and collect:

- Raw text
- Font size (used to determine hierarchy)
- Boldness (estimated from font name containing "Bold")
- X/Y coordinates (used to order content)
- Page number

We sort these blocks top-to-bottom for every page.

---

### 2. **Document Title Detection**

We extract the document title from **page 1** using this logic:

- Select lines with **largest font size**
- Filter lines with ≥ 2 words and ≥ 5 characters
- Choose the **top-most** (y0) block among largest-sized candidates

This heuristic ensures we reliably identify the main title even when styles vary.

---

### 3. **Form Detection (Optional Filtering)**

To avoid extracting headings from **application forms or templates**, we apply a form classification step:

- If a document contains ≥ 2 *strong form indicators* (e.g., “application form for grant”, “LTC advance”), or
- ≥ 4 *generic indicators* (e.g., “name of applicant”, “date of birth”),  
then the document is assumed to be a **form** and skipped (returns empty outline).

---

### 4. **Heading Detection (H1, H2, H3)**

This is the core logic of our pipeline. Each line is scored based on:

#### 💡 Scoring Logic:
| Feature            | Contribution |
|-------------------|--------------|
| Font size ≥ 16     | +3 points    |
| Font size ≥ 13     | +2 points    |
| Font size ≥ 11     | +1 point     |
| Bold font          | +1.5 points  |
| Numbered or semantic pattern (e.g. "1.2 Introduction") | +1.5 points |

#### ✨ Semantic Patterns Recognized:
- `1. Introduction`
- `1.1 Goals`
- `Chapter 1`, `Appendix A`, `Section 2`
- Common words like **Introduction**, **Background**, **Conclusion**, **References**, etc.

#### 📘 Heading Levels:
| Score Threshold | Heading Level |
|----------------|---------------|
| ≥ 5.0          | H1            |
| ≥ 4.0          | H2            |
| ≥ 3.0          | H3            |

---

## 📦 Output Format

For each `input.pdf`, the system produces `input.json` with the following structure:

```json
{
  "title": "Document Title",
  "outline": [
    { "level": "H1", "text": "Introduction", "page": 1 },
    { "level": "H2", "text": "Background", "page": 2 },
    { "level": "H3", "text": "Timeline", "page": 3 }
  ]
}

#### Directory Structure
.
├── app/
│   └── main.py             # Main script with the full processing logic
├── input/                  # Folder where input PDFs are mounted (empty in repo)
├── output/                 # Folder where output JSONs will be written
├── Dockerfile              # Container config
└── README.md               # This file


Build Docker Image

docker build --platform linux/amd64 -t mysolution:yourtag .


Run the Docker Container

docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none mysolution:yourtag





