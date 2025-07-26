import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import io
import json
import re
from PyPDF2 import PdfReader
from zipfile import ZipFile

st.set_page_config(page_title="PO Automation", layout="wide")
st.title("📄 Multi-PO Automation Tool")

uploaded_file = st.file_uploader("Upload a Purchase Order PDF (with multiple POs)", type="pdf")

# ---------- 1. Page-wise Text Extraction ----------

def extract_po_blocks_from_pdf(file_bytes):
    reader = PdfReader(io.BytesIO(file_bytes))
    po_blocks = []
    current_po = ""
    
    for page in reader.pages:
        text = page.extract_text()
        if not text:
            continue
        lines = text.split('\n')
        for line in lines:
            if re.match(r'Purchase\s+Order', line, re.I):
                if current_po:
                    po_blocks.append(current_po.strip())
                current_po = line + "\n"
            else:
                current_po += line + "\n"
    
    if current_po:
        po_blocks.append(current_po.strip())
    
    return po_blocks

# ---------- 2. Field Extractors ----------

def extract_main_fields(text):
    fields = {}
    fields['PO_Number'] = re.search(r'PO\s*(Number)?[:\s]*([A-Z0-9-]+)', text, re.I).group(2) if re.search(r'PO\s*(Number)?[:\s]*([A-Z0-9-]+)', text, re.I) else 'Not Found'
    fields['Vendor'] = re.search(r'Vendor[:\s]*(.+)', text, re.I).group(1).strip() if re.search(r'Vendor[:\s]*(.+)', text, re.I) else 'Not Found'
    fields['Address'] = re.search(r'Address[:\s]*(.+)', text, re.I).group(1).strip() if re.search(r'Address[:\s]*(.+)', text, re.I) else 'Not Found'
    fields['Date'] = re.search(r'Date[:\s]*([\d-]+)', text).group(1) if re.search(r'Date[:\s]*([\d-]+)', text) else 'Not Found'
    amt_match = re.search(r'Total\s*Amount[:\s₹Rs\.:]*([\d,]+\.\d{2})', text, re.I)
    fields['Total_Amount'] = amt_match.group(1).replace(',', '') if amt_match else 'Not Found'
    return fields

def extract_line_items_loose(text):
    lines = text.split('\n')
    items = []

    pattern1 = re.compile(
        r'(?P<desc>.+?)\s*[-–]?\s*(Qty|Quantity)[:\s]*(?P<qty>\d+)\s*[-–]?\s*(Unit Price|Price)[:\s₹Rs\.:]*(?P<price>[\d,]+\.\d{2})',
        re.I
    )

    pattern2 = re.compile(
        r'(?P<desc>[A-Za-z0-9\s\-.]+)\s+(?P<qty>\d{1,3})\s+([\₹Rs\.:]*)?(?P<price>[\d,]+\.\d{2})',
        re.I
    )

    for line in lines:
        match1 = pattern1.search(line)
        if match1:
            desc = re.sub(r'^\d+\.\s*', '', match1.group("desc").strip())
            qty = match1.group("qty")
            unit = match1.group("price").replace(",", "")
            total = f"{float(qty)*float(unit):.2f}"
            items.append({
                "Description": desc,
                "Quantity": qty,
                "Unit_Price": unit,
                "Total_Price": total
            })
            continue

        match2 = pattern2.search(line)
        if match2:
            desc = match2.group("desc").strip()
            qty = match2.group("qty")
            unit = match2.group("price").replace(",", "")
            total = f"{float(qty)*float(unit):.2f}"
            items.append({
                "Description": desc,
                "Quantity": qty,
                "Unit_Price": unit,
                "Total_Price": total
            })

    return pd.DataFrame(items)

# ---------- 3. Annotator ----------

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
        break  # Only annotate first PO
    doc.save("Annotated_PO.pdf")
    doc.close()

# ---------- 4. Streamlit App Logic ----------

if uploaded_file:
    st.info("✅ File uploaded. Extracting POs...")
    pdf_bytes = uploaded_file.read()
    
    po_blocks = extract_po_blocks_from_pdf(pdf_bytes)
    all_po_data = []
    all_items = []

    for block in po_blocks:
        fields = extract_main_fields(block)
        items_df = extract_line_items_loose(block)
        all_po_data.append({
            "PO_Fields": fields,
            "Line_Items": items_df.to_dict(orient="records")
        })
        for item in items_df.to_dict(orient="records"):
            item["PO_Number"] = fields["PO_Number"]
            all_items.append(item)

    # Display
    st.subheader("📋 PO Summary")
    st.dataframe(pd.DataFrame([po["PO_Fields"] for po in all_po_data]))

    st.subheader("📦 All Line Items")
    st.dataframe(pd.DataFrame(all_items))

    # Save files
    pd.DataFrame([po["PO_Fields"] for po in all_po_data]).to_excel("All_PO_Main_Fields.xlsx", index=False)
    pd.DataFrame(all_items).to_excel("All_PO_Line_Items.xlsx", index=False)

    with open("All_PO_Structured_Data.json", "w") as f:
        json.dump(all_po_data, f, indent=4)

    # Annotate 1st PO
    annotate_pdf(pdf_bytes, all_po_data[0]["PO_Fields"], pd.DataFrame(all_po_data[0]["Line_Items"]))

    # Zip
    with ZipFile("PO_Extraction_Outputs.zip", "w") as zipf:
        zipf.write("All_PO_Main_Fields.xlsx")
        zipf.write("All_PO_Line_Items.xlsx")
        zipf.write("All_PO_Structured_Data.json")
        zipf.write("Annotated_PO.pdf")

    with open("PO_Extraction_Outputs.zip", "rb") as f:
        st.download_button("📥 Download All Outputs", f, file_name="PO_Extraction_Outputs.zip")
