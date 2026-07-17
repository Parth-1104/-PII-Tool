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
        with st.spinner("Processing document structures and applying text/media masks..."):
            
            # Upper Edge Feature Setup: Define path to the custom visual compliance badge
            custom_badge_path = Path("redacted_placeholder.png")
            
            # Runtime fallback check: Generate a robust 1x1 light-gray PNG stream if the image isn't pushed yet
            if not custom_badge_path.exists():
                fallback_png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x01\x00\x00\x00\x1c\xf3\xffa\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
                custom_badge_path.write_bytes(fallback_png_bytes)
                
            try:
                # Run the pipeline passing down the custom compliance image target
                # (Note: Ensure your pipeline's underlying redact_document updates pass this to processor.process_and_redact)
                summary = pipeline.redact_document(
                    input_path=temp_input_path, 
                    output_path=temp_output_path, 
                    create_backup=False,
                    placeholder_image_path=custom_badge_path
                )
                
                st.balloons()
                st.success("Redaction Complete Across All Text & Media Layers!")
                
                # Display Summary Metrics Box
                st.markdown("### 📊 Redaction Audit Report")
                col1, col2, col3 = st.columns(3)
                col1.metric("Paragraphs Scanned", summary.get("paragraphs_processed", 0))
                col2.metric("Text Replacements", summary.get("total_replacements", 0))
                
                # Track and display the visual asset counts intercepted
                visual_swaps = summary.get("images_redacted", 0)
                col3.metric("Visual Assets Swapped", visual_swaps)
                
                # Expandable detailed metrics
                if "entity_counts" in summary and summary["entity_counts"]:
                    with st.expander("View Breakdown by PII Type"):
                        for pii_type, count in summary["entity_counts"].items():
                            st.write(f"🔹 **{pii_type}**: {count} replacements")
                        if visual_swaps > 0:
                            st.write(f"🖼️ **VISUAL_COMPLIANCE_MEDIA**: {visual_swaps} images overwritten")
                
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
                # Clean up temporary disk files safely to prevent memory bloat on server nodes
                if temp_input_path.exists():
                    os.remove(temp_input_path)
                if temp_output_path.exists():
                    try:
                        os.remove(temp_output_path)
                    except:
                        pass