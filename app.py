import streamlit as st
import os
from pathlib import Path
from src.pipeline.redactor_pipeline import RedactionPipeline

st.set_page_config(page_title="PII Redaction Engine", page_icon="🔒", layout="centered")

st.title("🔒 Industrial PII Redaction Tool")
st.write("Upload any `.docx` document to automatically replace sensitive information (Names, Emails, Companies, Addresses) with realistic synthetic data.")

# Initialize the pipeline in cache so it doesn't reload the AI models on every click
@st.cache_resource
def load_pipeline():
    return RedactionPipeline(
        config_path=None,
        score_threshold=0.65,
        enable_persistence=True,
        persistence_path="./web_entity_vault.json"
    )

try:
    pipeline = load_pipeline()
except Exception as e:
    st.error(f"Failed to initialize the NLP pipeline: {e}")
    st.stop()

# File Upload Element
uploaded_file = st.file_uploader("Choose a Microsoft Word Document (.docx)", type=["docx"])

if uploaded_file is not None:
    # Save the uploaded file temporarily to disk
    temp_input_path = Path(f"temp_input_{uploaded_file.name}")
    temp_output_path = Path(f"redacted_{uploaded_file.name}")
    
    with open(temp_input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    st.success("File uploaded successfully!")
    
    # Trigger Redaction Process
    if st.button("🚀 Run PII Redaction"):
        with st.spinner("Processing document text structures and applying synthetic masks..."):
            try:
                # Run the pipeline
                summary = pipeline.redact_document(temp_input_path, temp_output_path, create_backup=False)
                
                st.balloons()
                st.success("Redaction Complete!")
                
                # Display Summary Metrics Box
                st.markdown("### 📊 Redaction Audit Report")
                col1, col2 = st.columns(2)
                col1.metric("Paragraphs Scanned", summary["paragraphs_processed"])
                col2.metric("Total Replacements", summary["total_replacements"])
                
                # Expandable detailed metrics
                with st.expander("View Breakdown by PII Type"):
                    for pii_type, count in summary["entity_counts"].items():
                        st.write(f"🔹 **{pii_type}**: {count} replacements")
                
                # Read the file back into memory for the download button
                with open(temp_output_path, "rb") as file_bytes:
                    st.download_button(
                        label="📥 Download Redacted Document",
                        data=file_bytes,
                        file_name=f"Redacted_{uploaded_file.name}",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                    
            except Exception as err:
                st.error(f"An error occurred during processing: {err}")
            finally:
                # Clean up temporary disk files safely
                if temp_input_path.exists():
                    os.remove(temp_input_path)
                if temp_output_path.exists():
                    try:
                        os.remove(temp_output_path)
                    except:
                        pass