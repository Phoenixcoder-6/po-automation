import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import io
import json
import re
import pdfplumber
from zipfile import ZipFile

st.set_page_config(page_title="PO Automation", layout="wide")
st.title("📄 Multi-PO Automation Tool")

uploaded_file = st.file_uploader("Upload a Purchase Order PDF (even with multiple POs)", type="pdf")

# ---------- Helper Functions ----------

def extract_text_blocks(file_bytes):
    full_text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"
    # Split POs based on "Purchase Order"
    blocks = re.split(r'(?=Purchase Order)', full_text, flags=re.IGNORECASE)
    return [b.strip() for b in blocks if b.strip()]

def extract_main_fields(text):
    fields = {}
    fields['PO_Number'] = re.search(r'PO\s*(Number)?[:\s]*([A-Z0-9-]+)', text, re.I).group(2) if re.search(r'PO\s*(Number)?[:\s]*([A-Z0-9-]+)', text, re.I) else 'Not Found'
    fields['Vendor'] = re.search(r'Vendor[:\s]*(.+)', text, re.I).group(1).strip() if re.search(r'Vendor[:\s]*(.+)', text, re.I) else 'Not Found'
    fields['Address'] = re.search(r'Address[:\s]*(.+)', text, re.I).group(1).strip() if re.search(r'Address[:\s]*(.+)', text, re.I) else 'Not Found'
    fields['Date'] = re.search(r'Date[:\s]*([\d-]+)', text).group(1) if re.search(r'Date[:\s]*([\d-]+)', text) else 'Not Found'
    amt_match = re.search(r'Total\s*Amount[:\s₹Rs\.:]*([\d,]+\.\d{2})', text, re.I)
    fields['Total_Amount'] = amt_match.group(1).replace(',', '') if amt_match else 'Not Found'
    return fields

def smart_merge_lines(lines):
    merged = []
    buffer = ""
    for line in lines:
        if re.match(r'^\s*\d+\.', line):
            if buffer:
                merged.append(buffer.strip())
            buffer = line.strip()
        else:
            buffer += " " + line.strip()
    if buffer:
        merged.append(buffer.strip())
    return merged

def extract_line_items(text):
    raw_lines = text.split('\n')
    lines = smart_merge_lines(raw_lines)
    items = []

    pattern = re.compile(
        r'^\s*\d+\.\s*(.+?)\s*[-–]?\s*(Qty|Quantity)[:\s]*(\d+)\s*[-–]?\s*(Unit Price|Price)[:\s₹Rs\.:]*(\d{1,3}(?:,\d{3})*\.\d{2})',
        re.I
    )

    for line in lines:
        match = pattern.search(line)
        if match:
            desc = match.group(1).strip()
            qty = match.group(3)
            unit = match.group(5).replace(",", "")
            total = f"{float(qty)*float(unit):.2f}"
            items.append({
                "Description": desc,
                "Quantity": qty,
                "Unit_Price": unit,
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
        break
    doc.save("Annotated_PO.pdf")
    doc.close()

# ---------- Main App Logic ----------

if uploaded_file:
    st.info("✅ File uploaded. Processing all PO blocks...")

    pdf_bytes = uploaded_file.read()
    po_blocks = extract_text_blocks(pdf_bytes)

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

    # Display
    st.subheader("📋 Extracted PO Fields")
    st.dataframe(pd.DataFrame([po["PO_Fields"] for po in all_po_data]))

    st.subheader("📦 Extracted Line Items")
    st.dataframe(pd.DataFrame(all_items))

    # Save
    pd.DataFrame([po["PO_Fields"] for po in all_po_data]).to_excel("All_PO_Main_Fields.xlsx", index=False)
    pd.DataFrame(all_items).to_excel("All_PO_Line_Items.xlsx", index=False)
    with open("All_PO_Structured_Data.json", "w") as f:
        json.dump(all_po_data, f, indent=4)

    # Annotate first PO
    annotate_pdf(pdf_bytes, all_po_data[0]["PO_Fields"], pd.DataFrame(all_po_data[0]["Line_Items"]))

    # Bundle
    with ZipFile("PO_Extraction_Outputs.zip", "w") as zipf:
        zipf.write("All_PO_Main_Fields.xlsx")
        zipf.write("All_PO_Line_Items.xlsx")
        zipf.write("All_PO_Structured_Data.json")
        zipf.write("Annotated_PO.pdf")

    with open("PO_Extraction_Outputs.zip", "rb") as f:
        st.download_button("📥 Download All Extracted Outputs", f, file_name="PO_Extraction_Outputs.zip")
