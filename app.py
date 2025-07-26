import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import io
import json
import re
from PyPDF2 import PdfReader
from pdf2image import convert_from_bytes
import pytesseract
from zipfile import ZipFile

st.set_page_config(page_title="PO Automation", layout="wide")
st.title("📄 Multi-PO Automation Tool (Advanced)")

uploaded_file = st.file_uploader("Upload a Purchase Order PDF (even with multiple POs)", type="pdf")

# ---------- OCR + Text Extraction ----------

def extract_text_from_pdf(file_bytes):
    try:
        pdf_stream = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_stream)
        full_text = "\n".join([page.extract_text() or '' for page in reader.pages])
        if full_text.strip():
            return full_text
        else:
            raise ValueError("No text layer found, fallback to OCR")
    except:
        # OCR fallback
        images = convert_from_bytes(file_bytes)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img) + "\n"
        return text

# ---------- Helper Functions ----------

def split_po_blocks(text):
    blocks = re.split(r'(?=Purchase Order)', text, flags=re.IGNORECASE)
    return [b.strip() for b in blocks if b.strip()]

def extract_main_fields(text):
    def extract(pattern, group=1, default='Not Found'):
        match = re.search(pattern, text, re.I)
        return match.group(group).strip() if match else default

    return {
        'PO_Number': extract(r'PO\s*(Number)?[:\s]*([A-Z0-9-]+)', 2),
        'Vendor': extract(r'Vendor[:\s]*(.+)'),
        'Address': extract(r'Address[:\s]*(.+)'),
        'Date': extract(r'Date[:\s]*([\d-]+)'),
        'Total_Amount': extract(r'Total\s*Amount[:\s₹Rs\.:]*([\d,]+\.\d{2})').replace(',', '')
    }

def extract_line_items(text):
    items = []
    lines = text.split('\n')

    for line in lines:
        line = line.strip()

        # Pattern 1: 1. Item - Qty: X - Price: ₹Y
        m1 = re.match(r'\d+\.\s*(.*?)\s*[-–]\s*Qty[:\s]*(\d+)\s*[-–]\s*(Unit Price|Price)[:\s₹Rs\.:]*(\d[\d,]*\.\d{2})', line, re.I)
        if m1:
            desc = m1.group(1).strip()
            qty = m1.group(2)
            price = m1.group(4).replace(",", "")
            total = f"{float(qty)*float(price):.2f}"
            items.append({
                "Description": desc,
                "Quantity": qty,
                "Unit_Price": price,
                "Total_Price": total
            })
            continue

        # Pattern 2: ItemName    Qty    Price
        m2 = re.match(r'([A-Za-z0-9\s\-.]+)\s+(\d{1,3})\s+([\₹Rs\.:]*)?([\d,]+\.\d{2})', line, re.I)
        if m2:
            desc = m2.group(1).strip()
            qty = m2.group(2)
            price = m2.group(4).replace(",", "")
            total = f"{float(qty)*float(price):.2f}"
            items.append({
                "Description": desc,
                "Quantity": qty,
                "Unit_Price": price,
                "Total_Price": total
            })

    return pd.DataFrame(items)

def annotate_pdf(file_bytes, fields, items):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    for page in doc:
        for val in fields.values():
            if val != "Not Found":
                for rect in page.search_for(str(val)):
                    page.add_highlight_annot(rect)
        for _, row in items.iterrows():
            for rect in page.search_for(str(row['Description'])):
                page.add_rect_annot(rect)
        break  # Only first PO
    doc.save("Annotated_PO.pdf")
    doc.close()

# ---------- Main Streamlit Logic ----------

if uploaded_file:
    st.info("✅ File uploaded. Processing...")

    pdf_bytes = uploaded_file.read()
    full_text = extract_text_from_pdf(pdf_bytes)

    po_blocks = split_po_blocks(full_text)
    all_po_data = []
    all_items = []

    for block in po_blocks:
        fields = extract_main_fields(block)
        items_df = extract_line_items(block)
        all_po_data.append({
            "PO_Fields": fields,
            "Line_Items": items_df.to_dict(orient="records")
        })
        for item in items_df.to_dict(orient="records"):
            item["PO_Number"] = fields["PO_Number"]
            all_items.append(item)

    st.subheader("📋 All Extracted PO Fields")
    st.dataframe(pd.DataFrame([po["PO_Fields"] for po in all_po_data]))

    st.subheader("📦 All Extracted Line Items")
    st.dataframe(pd.DataFrame(all_items))

    # Save outputs
    pd.DataFrame([po["PO_Fields"] for po in all_po_data]).to_excel("All_PO_Main_Fields.xlsx", index=False)
    pd.DataFrame(all_items).to_excel("All_PO_Line_Items.xlsx", index=False)

    with open("All_PO_Structured_Data.json", "w") as f:
        json.dump(all_po_data, f, indent=4)

    # Annotate PDF
    annotate_pdf(pdf_bytes, all_po_data[0]["PO_Fields"], pd.DataFrame(all_po_data[0]["Line_Items"]))

    # Bundle
    with ZipFile("PO_Extraction_Outputs.zip", "w") as zipf:
        zipf.write("All_PO_Main_Fields.xlsx")
        zipf.write("All_PO_Line_Items.xlsx")
        zipf.write("All_PO_Structured_Data.json")
        zipf.write("Annotated_PO.pdf")

    with open("PO_Extraction_Outputs.zip", "rb") as f:
        st.download_button("📥 Download All Extracted Outputs", f, file_name="PO_Extraction_Outputs.zip")

