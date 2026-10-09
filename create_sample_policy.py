import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_insurance_pdf(pdf_path="sample_insurance_policy.pdf", txt_path="sample_insurance_policy.txt"):
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0d3b66'),
        alignment=1, # Center
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0d3b66'),
        spaceBefore=12,
        spaceAfter=6
    )
    
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor('#f95738'),
        spaceBefore=6,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#222222'),
        spaceAfter=4
    )

    story = []

    # Title
    story.append(Paragraph("STAR HEALTH SHIELD COMPREHENSIVE POLICY", title_style))
    story.append(Paragraph("<b>Policy Document & Terms of Coverage</b> | Policy No: <b>SHS-POL-2026-98124</b>", ParagraphStyle('Sub', parent=body_style, alignment=1, textColor=colors.HexColor('#555555'))))
    story.append(Spacer(1, 10))

    # Policy Schedule Table
    story.append(Paragraph("POLICY SCHEDULE & SUMMARY", h1_style))
    schedule_data = [
        [Paragraph("<b>Parameter</b>", body_style), Paragraph("<b>Policy Details</b>", body_style)],
        [Paragraph("Insured Person", body_style), Paragraph("Rahul Sharma (Age: 42 Years)", body_style)],
        [Paragraph("Sum Insured (SI)", body_style), Paragraph("INR 5,00,000 (Five Lakhs Only)", body_style)],
        [Paragraph("Policy Period", body_style), Paragraph("01-Jan-2026 to 31-Dec-2026", body_style)],
        [Paragraph("Base Deductible", body_style), Paragraph("INR 10,000 per policy year", body_style)],
        [Paragraph("Co-Payment", body_style), Paragraph("10% co-pay applicable if age >= 60; Nil for age < 60", body_style)],
        [Paragraph("No Claim Bonus (NCB)", body_style), Paragraph("10% SI increase per claim-free year, max up to 50%", body_style)],
        [Paragraph("Geographical Scope", body_style), Paragraph("India (Network & Non-Network Hospitals)", body_style)],
    ]
    t = Table(schedule_data, colWidths=[180, 330])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e0eaf4')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#aaaaaa')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Section 1: Definitions
    story.append(Paragraph("SECTION 1: KEY DEFINITIONS", h1_style))
    story.append(Paragraph("<b>1.1 Accident:</b> An accident means a sudden, unforeseen, and involuntary event caused by external, violent, and visible means.", body_style))
    story.append(Paragraph("<b>1.2 Cashless Facility:</b> A facility extended by the insurer where payments for treatment at network hospitals are directly settled by the insurer or TPA.", body_style))
    story.append(Paragraph("<b>1.3 Co-Payment:</b> A cost-sharing requirement where the insured will bear a specified percentage of the admissible claim amount.", body_style))
    story.append(Paragraph("<b>1.4 Deductible:</b> A cost-sharing requirement that provides that the insurer will not be liable for a specified rupee amount of the covered expenses.", body_style))
    story.append(Paragraph("<b>1.5 Day Care Treatment:</b> Medical treatment and/or surgical procedures undertaken under general or local anesthesia in a hospital/day care center in less than 24 hours.", body_style))
    story.append(Paragraph("<b>1.6 Grace Period:</b> A period of 30 days immediately following the premium due date during which payment can be made without loss of continuity benefits.", body_style))
    story.append(Paragraph("<b>1.7 Pre-Existing Disease (PED):</b> Any condition, ailment, injury, or disease diagnosed by a physician or for which medical advice or treatment was received within 36 months prior to the effective date of the policy.", body_style))
    story.append(Paragraph("<b>1.8 Room Rent:</b> The amount charged by a hospital towards the occupancy of a bed on per day basis.", body_style))

    # Section 2: Scope of Coverage
    story.append(Paragraph("SECTION 2: SCOPE OF COVERAGE & INCLUSIONS", h1_style))
    story.append(Paragraph("<b>2.1 In-Patient Hospitalization:</b> Reasonable and customary medical expenses incurred for hospitalization exceeding 24 consecutive hours for covered illness or injury.", body_style))
    story.append(Paragraph("<b>2.2 Pre-Hospitalization Expenses:</b> Medical expenses incurred up to <b>60 days</b> immediately prior to hospitalization admission are covered, provided related to the same condition.", body_style))
    story.append(Paragraph("<b>2.3 Post-Hospitalization Expenses:</b> Medical expenses incurred up to <b>90 days</b> immediately following discharge are covered.", body_style))
    story.append(Paragraph("<b>2.4 Day Care Procedures:</b> 405 listed daycare procedures that do not require 24-hour hospitalization due to technological advancements are covered up to the full Sum Insured.", body_style))
    story.append(Paragraph("<b>2.5 AYUSH Treatment:</b> In-patient hospitalization under Ayurveda, Yoga, Unani, Siddha, and Homeopathy in government-recognized healthcare institutions is covered up to <b>100% of the Sum Insured</b>.", body_style))
    story.append(Paragraph("<b>2.6 Road Ambulance:</b> Emergency road ambulance expenses covered up to a limit of <b>INR 2,500 per hospitalization episode</b>.", body_style))
    story.append(Paragraph("<b>2.7 Modern & Robotic Surgeries:</b> Cutting-edge procedures including robotic surgeries, balloon sinuplasty, deep brain stimulation, and stem cell therapy covered up to <b>50% of the Sum Insured</b>.", body_style))

    # Section 3: Sub-limits and Capping Table
    story.append(Paragraph("SECTION 3: SUB-LIMITS AND CAPPING", h1_style))
    sublimits_data = [
        [Paragraph("<b>Treatment / Expense Category</b>", body_style), Paragraph("<b>Sub-Limit / Capping</b>", body_style)],
        [Paragraph("Room Rent & Boarding Charges", body_style), Paragraph("Capped at <b>1% of Sum Insured per day</b> (INR 5,000/day for INR 5 Lakh SI)", body_style)],
        [Paragraph("Intensive Care Unit (ICU) Charges", body_style), Paragraph("Capped at <b>2% of Sum Insured per day</b> (INR 10,000/day for INR 5 Lakh SI)", body_style)],
        [Paragraph("Cataract Surgery", body_style), Paragraph("Maximum <b>INR 40,000 per eye</b>, or actuals, whichever is lower", body_style)],
        [Paragraph("Joint Replacement Surgery", body_style), Paragraph("Maximum <b>INR 1,50,000 per policy year</b> (except if due to accident)", body_style)],
        [Paragraph("Proportionate Deduction Clause", body_style), Paragraph("If insured occupies room higher than limit, associated expenses are deducted proportionally", body_style)],
    ]
    t2 = Table(sublimits_data, colWidths=[200, 310])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#fde2e4')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#aaaaaa')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t2)
    story.append(Spacer(1, 8))

    # Section 4: Waiting Periods
    story.append(Paragraph("SECTION 4: WAITING PERIODS", h1_style))
    story.append(Paragraph("<b>4.1 Initial Waiting Period (30 Days):</b> An initial waiting period of 30 days from policy inception date applies to all medical treatments, except hospitalization necessitated directly by an <b>Accident</b>.", body_style))
    story.append(Paragraph("<b>4.2 Specific Illness Waiting Period (24 Months):</b> A waiting period of 24 months continuous coverage applies to specified conditions including: Cataract, Hernia, Hydrocele, Sinusitis, Gallbladder & Kidney stones, Piles, Benign Prostatic Hypertrophy (BPH), and Osteoarthritis.", body_style))
    story.append(Paragraph("<b>4.3 Pre-Existing Diseases (PED) Waiting Period (36 Months):</b> All pre-existing conditions, illnesses, or related complications are excluded until the insured has completed <b>36 months of continuous coverage</b>.", body_style))

    # Section 5: Exclusions
    story.append(Paragraph("SECTION 5: PERMANENT EXCLUSIONS", h1_style))
    story.append(Paragraph("The insurer shall not be liable to make any payment under this policy in respect of:", body_style))
    story.append(Paragraph("• <b>Cosmetic Surgery:</b> Aesthetic treatment, plastic surgery, or circumcision unless necessitated by accident or burn.", body_style))
    story.append(Paragraph("• <b>Substance Abuse & Self-Injury:</b> Treatment arising from intentional self-harm, attempted suicide, alcohol abuse, or narcotics.", body_style))
    story.append(Paragraph("• <b>Hazardous Sports:</b> Professional participation in hazardous or adventure sports (motor racing, skydiving, mountaineering).", body_style))
    story.append(Paragraph("• <b>Dental & Vision:</b> Routine dental treatment or eye glasses/contact lenses unless necessitated by trauma requiring hospital admission.", body_style))
    story.append(Paragraph("• <b>Maternity & Childbirth:</b> Pregnancy, childbirth, abortion, and fertility treatments (unless separate maternity rider opted).", body_style))
    story.append(Paragraph("• <b>War & Nuclear Risks:</b> Injuries caused by nuclear weapons, radiation, war, or invasion.", body_style))

    # Section 6: Claim Procedure
    story.append(Paragraph("SECTION 6: CLAIM INTIMATION & SUBMISSION PROCEDURE", h1_style))
    story.append(Paragraph("<b>6.1 Cashless Claims:</b> For planned hospitalization, intimation must be submitted to the TPA at least <b>48 hours before admission</b>. For emergency admission, notice must be given within <b>24 hours of hospitalization</b>.", body_style))
    story.append(Paragraph("<b>6.2 Reimbursement Claims:</b> Intimate insurer within 48 hours. The completed claim form along with original discharge summary, hospital bills, pharmacy receipts, and diagnostic reports must be submitted within <b>30 days of hospital discharge</b>.", body_style))

    # Section 7: General Terms
    story.append(Paragraph("SECTION 7: GENERAL TERMS & CONDITIONS", h1_style))
    story.append(Paragraph("<b>7.1 Grace Period:</b> A grace period of <b>30 days</b> is allowed for renewal premium payment without break in policy continuity.", body_style))
    story.append(Paragraph("<b>7.2 Free-Look Period:</b> The insured has <b>15 days</b> from receipt of policy to review terms and seek cancellation with pro-rata refund minus stamp duty.", body_style))
    story.append(Paragraph("<b>7.3 Portability:</b> Policyholders can port their policy to another insurer by applying at least <b>45 days prior</b> to premium renewal date.", body_style))

    doc.build(story)
    print(f"[+] Successfully generated PDF at: {pdf_path}")

    # Also save as clean plain text
    txt_content = """STAR HEALTH SHIELD COMPREHENSIVE POLICY
Policy Document & Terms of Coverage | Policy No: SHS-POL-2026-98124

POLICY SCHEDULE & SUMMARY:
- Insured Person: Rahul Sharma (Age: 42 Years)
- Sum Insured (SI): INR 5,00,000 (Five Lakhs Only)
- Policy Period: 01-Jan-2026 to 31-Dec-2026
- Base Deductible: INR 10,000 per policy year
- Co-Payment: 10% co-pay applicable if age >= 60; Nil for age < 60
- No Claim Bonus (NCB): 10% SI increase per claim-free year, max up to 50%
- Geographical Scope: India (Network & Non-Network Hospitals)

SECTION 1: KEY DEFINITIONS
1.1 Accident: A sudden, unforeseen, and involuntary event caused by external, violent, and visible means.
1.2 Cashless Facility: Payments for treatment at network hospitals are settled directly by the insurer/TPA.
1.3 Co-Payment: Cost-sharing requirement where insured bears a specified percentage of admissible claim amount.
1.4 Deductible: A specified rupee amount (INR 10,000) that insured must pay before insurer liability begins.
1.5 Day Care Treatment: Surgical procedures under anesthesia completed in hospital in less than 24 hours.
1.6 Grace Period: 30 days following premium due date during which payment can be made without loss of continuity benefits.
1.7 Pre-Existing Disease (PED): Any condition diagnosed or treated within 36 months prior to policy inception.
1.8 Room Rent: The amount charged by hospital for occupancy of a bed per day.

SECTION 2: SCOPE OF COVERAGE & INCLUSIONS
2.1 In-Patient Hospitalization: Medical expenses for hospitalization exceeding 24 consecutive hours.
2.2 Pre-Hospitalization: Medical expenses incurred up to 60 days prior to hospital admission.
2.3 Post-Hospitalization: Medical expenses incurred up to 90 days after discharge from hospital.
2.4 Day Care Procedures: 405 listed daycare procedures covered up to full Sum Insured without 24hr stay.
2.5 AYUSH Treatment: In-patient treatment under Ayurveda, Yoga, Unani, Siddha, Homeopathy covered up to 100% of Sum Insured.
2.6 Road Ambulance: Emergency ambulance covered up to INR 2,500 per hospitalization episode.
2.7 Modern & Robotic Surgeries: Robotic surgery, deep brain stimulation, stem cell therapy covered up to 50% of Sum Insured.

SECTION 3: SUB-LIMITS AND CAPPING
3.1 Room Rent & Boarding Charges: Capped at 1% of Sum Insured per day (INR 5,000/day for INR 5,00,000 SI). Proportionate deduction applies to all medical expenses if higher room category is occupied.
3.2 Intensive Care Unit (ICU): Capped at 2% of Sum Insured per day (INR 10,000/day for INR 5,00,000 SI).
3.3 Cataract Surgery: Maximum INR 40,000 per eye, or actual cost, whichever is lower.
3.4 Joint Replacement Surgery: Maximum INR 1,50,000 per policy year, unless caused by accidental bodily injury.

SECTION 4: WAITING PERIODS
4.1 Initial Waiting Period (30 Days): 30 days from policy inception date for any illness. No waiting period for Accidental injuries.
4.2 Specific Illness Waiting Period (24 Months): 24 months continuous coverage required for Cataract, Hernia, Hydrocele, Sinusitis, Kidney/Gallbladder stones, Piles, BPH, and Osteoarthritis.
4.3 Pre-Existing Disease (PED) Waiting Period (36 Months): 36 months continuous coverage required before pre-existing disease claims are admissible.

SECTION 5: PERMANENT EXCLUSIONS
- Cosmetic, aesthetic, or plastic surgery unless caused by accidental burns or injury.
- Intentional self-harm, attempted suicide, alcohol abuse, or drug addiction treatments.
- Hazardous or adventure sports participation.
- Routine dental treatment or eye glasses/contact lenses unless necessitated by trauma.
- Maternity expenses and childbirth (unless separate rider opted).
- War, nuclear radiation, and invasion injuries.

SECTION 6: CLAIM INTIMATION & SUBMISSION PROCEDURE
6.1 Cashless Claims: Planned hospitalization requires 48 hours prior notice to TPA; emergency admission requires notice within 24 hours.
6.2 Reimbursement Claims: Intimation within 48 hours. Claim forms, discharge summary, original bills, and receipts must be submitted within 30 days of discharge.

SECTION 7: GENERAL TERMS & CONDITIONS
7.1 Grace Period: 30 days allowed for renewal premium payment without losing continuity benefits.
7.2 Free-Look Period: 15 days from policy document receipt to cancel and receive refund minus stamp duty.
7.3 Portability: Application to port to another insurer must be submitted at least 45 days prior to renewal date.
"""
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)
    print(f"[+] Successfully generated TXT at: {txt_path}")

if __name__ == "__main__":
    generate_insurance_pdf()
