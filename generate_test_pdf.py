from fpdf import FPDF

pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)

for page_num in range(1, 501):
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"RFP Master Document - Page {page_num}", ln=True, align='C')
    
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.multi_cell(0, 10, f"""This is page {page_num} of the generated 500-page RFP Test Document.

1. Scope of Work (Section {page_num})
The contractor shall provide cloud-native generative AI infrastructure that adheres to the compliance metrics outlined in this document. This includes establishing a robust multi-region deployment strategy.

2. Technical Requirements
- Requirement {page_num}.A: Must support auto-scaling up to {page_num * 100} concurrent users.
- Requirement {page_num}.B: Must integrate with enterprise SSO (SAML 2.0 / OIDC).
- Requirement {page_num}.C: Ensure end-to-end encryption at rest and in transit using AES-256.

3. Evaluation Criteria
All vendor submissions will be evaluated against the standard SLA matrix. Page {page_num} specific metrics apply to the uptime guarantee of 99.99%.

4. Pricing & SLA
The estimated budget for module {page_num} is ${page_num * 500}. Additional licensing fees must be detailed in Appendix C.

(End of Page {page_num} content)
""")

pdf.output("Test_RFP_500_Pages.pdf")
print("PDF created successfully!")
