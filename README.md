
# 📄 Multi-PO Automation Tool

> A Streamlit-powered application to extract structured purchase order (PO) data—including vendor details and line items—from scanned or digital PDFs using intelligent parsing and regex techniques.

---

## 🚀 Why This Project?

Organizations deal with **thousands of purchase orders (POs)** daily, many of which are unstructured PDFs—scanned, poorly formatted, or handwritten. Manual entry or parsing of such documents is time-consuming, error-prone, and inefficient.

This tool automates the extraction of **key fields and line items** from single or multi-PO PDFs, saving hours of manual labor while improving accuracy.

---

## 🧠 Project Idea

The goal is to build a **lightweight, interactive PO extraction system** that:
- Processes multiple POs from a single PDF file.
- Extracts key metadata (PO number, vendor, address, date, total).
- Parses line items using robust pattern-matching techniques.
- Supports non-tabular and scanned PDF formats (OCR-ready architecture).
- Allows easy download of structured results (Excel, JSON, Annotated PDF).

---

## 💼 Applications

| Domain | Use Case |
|--------|----------|
| 🏢 Enterprises | Automate invoice/PO processing in procurement & finance teams. |
| 📦 Supply Chain | Quickly parse bulk POs to match items with inventory or shipment data. |
| 🏛️ Government | Speed up document digitization and archival of procurement files. |
| 📊 Data Entry Automation | Reduce cost and increase throughput for data entry BPOs. |
| 🧾 Audit & Compliance | Extract structured logs for analysis and cross-verification. |

---

## 📂 Features

- ✅ **Multi-PO Extraction**: Supports one or many purchase orders in a single PDF.
- 🧠 **Regex + NLP Parsing**: Extracts line items from raw text without relying on tables.
- 📸 **PDF Annotation**: Highlights extracted values in the PDF using PyMuPDF.
- 💾 **Download Outputs**: Exports structured JSON, Excel files, and annotated PDF.
- 🎛️ **Streamlit UI**: Clean, user-friendly interface for drag-and-drop uploads.
- 📜 **OCR-Ready**: Can be extended to support scanned PDFs using `pytesseract`.

---

## 🛠️ Tech Stack

- **Python 3.8+**
- [Streamlit](https://streamlit.io/)
- [pdfplumber](https://github.com/jsvine/pdfplumber) (for text extraction)
- [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/en/latest/) (for PDF annotation)
- [re (Regex)](https://docs.python.org/3/library/re.html) (for field & item parsing)
- [pandas](https://pandas.pydata.org/) (for structured data)
- `zipfile`, `io`, `json` for file handling and downloads

---

## 🖥️ How It Works

1. **Upload PDF** – Drag and drop a purchase order PDF (with single or multiple POs).
2. **Text Parsing** – The PDF is parsed using `pdfplumber`; text is split into PO blocks.
3. **Field Extraction** – Key metadata is extracted using regex:
    - `PO_Number`
    - `Vendor`
    - `Address`
    - `Date`
    - `Total_Amount`
4. **Line Item Extraction** – Each block is scanned for itemized purchases using flexible regex:
    ```
    e.g., HP Printer 123 - Qty: 2 - Price: 1200.00
    ```
5. **Annotation** – Values are highlighted in the original PDF using `fitz`.
6. **Download** – Outputs available in:
    - 📄 `All_PO_Main_Fields.xlsx`
    - 📦 `All_PO_Line_Items.xlsx`
    - 🔖 `Annotated_PO.pdf`
    - 🧾 `All_PO_Structured_Data.json`
    - 🗜️ All bundled in a downloadable ZIP.

---

## 📌 PDF Format Guidelines

To ensure accurate parsing, your POs should follow this **ideal structure**:

