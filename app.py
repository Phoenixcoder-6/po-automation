import streamlit as st # type: ignore
import pandas as pd
import fitz  # type: ignore # PyMuPDF
import io
import json
import re
from PyPDF2 import PdfReader # type: ignore
from zipfile import ZipFile

st.set_page_config(page_title="PO Automation", layout="wide")
st.title("📄 Purchase Order Automation Tool")

uploaded_file = st.file_uploader("Upload a Purchase Order PDF", type="pdf")

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
    lines = text.split("\n")
    items = []
    pattern = re.compile(r'(.+?)\s*-\s*Qty[:\s]*(\d+)\s*-\s*Unit Price[:\s₹Rs\.:]*([\d,]+\.\d{2})', re.I)
    for line in lines:
        m = pattern.search(line)
        if m:
            desc = re.sub(r'^\d+\.\s*', '', m.group(1).strip())
            qty = m.group(2)
            unit = m.group(3).replace(',', '')
            total = f"{float(qty)*float(unit):.2f}"
            items.append({"Description": desc, "Quantity": qty, "Unit_Price": unit, "Total_Price": total})
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
    output_pdf = "Annotated_PO.pdf"
    doc.save(output_pdf)
    doc.close()
    return output_pdf

if uploaded_file:
    st.info("✅ File uploaded. Processing...")
    pdf_bytes = uploaded_file.read()
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])

    fields = extract_main_fields(text)
    items_df = extract_line_items_loose(text)

    st.subheader("📋 Extracted Main PO Fields")
    st.json(fields)

    st.subheader("📦 Extracted Line Items")
    st.dataframe(items_df)

    # Save files
    main_df = pd.DataFrame([fields])
    main_df.to_excel("PO_Main_Fields.xlsx", index=False)
    items_df.to_excel("PO_Line_Items.xlsx", index=False)

    with open("PO_Structured_Data.json", "w") as f:
        json.dump({
            "Main_Fields": fields,
            "Line_Items": items_df.to_dict(orient="records")
        }, f, indent=4)

    # Annotate and save
    pdf_output = annotate_pdf(pdf_bytes, fields, items_df)

    # Bundle
    with ZipFile("PO_Extraction_Outputs.zip", "w") as zipf:
        zipf.write("PO_Main_Fields.xlsx")
        zipf.write("PO_Line_Items.xlsx")
        zipf.write("PO_Structured_Data.json")
        zipf.write(pdf_output)

    with open("PO_Extraction_Outputs.zip", "rb") as f:
        st.download_button("📥 Download All Extracted Files", f, file_name="PO_Extraction_Outputs.zip")
