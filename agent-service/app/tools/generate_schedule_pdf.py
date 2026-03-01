"""
CareTopicz — Patient Medication Schedule PDF Generator
Generates a professional clinical PDF with patient info, screening results,
medication schedule, and appointment details.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime


def generate_schedule_pdf(patient_data: dict, output_path: str = "patient_schedule.pdf"):
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        topMargin=0.5*inch, bottomMargin=0.75*inch,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
    )
    styles = getSampleStyleSheet()
    teal = colors.HexColor("#1A7A73")
    light_teal = colors.HexColor("#E6F5F3")

    styles.add(ParagraphStyle(name='ClinicName', parent=styles['Normal'], fontSize=18, leading=22, textColor=teal, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Subtitle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor("#6B7280"), fontName='Helvetica'))
    styles.add(ParagraphStyle(name='SectionHeader', parent=styles['Normal'], fontSize=12, leading=16, textColor=colors.white, fontName='Helvetica-Bold', spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name='FieldLabel', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor("#6B7280"), fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='FieldValue', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor("#111827"), fontName='Helvetica'))
    styles.add(ParagraphStyle(name='Footer', parent=styles['Normal'], fontSize=7, leading=10, textColor=colors.HexColor("#9CA3AF"), fontName='Helvetica', alignment=TA_CENTER))

    story = []

    # Header
    header_data = [[
        Paragraph(patient_data.get("clinic_name", "Great Clinic"), styles['ClinicName']),
        Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>Schedule ID: {patient_data.get('schedule_id', 'N/A')}", styles['Subtitle']),
    ]]
    ht = Table(header_data, colWidths=[4*inch, 3*inch])
    ht.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
    story.append(ht)
    story.append(Spacer(1, 2))
    story.append(Paragraph("Medication Schedule — Biologic Therapy", styles['Subtitle']))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=2, color=teal))
    story.append(Spacer(1, 12))

    def section_header(text):
        t = Table([[Paragraph(text, styles['SectionHeader'])]], colWidths=[7*inch], rowHeights=[22])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), teal), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3), ('LEFTPADDING', (0,0), (-1,-1), 8)]))
        return t

    # Patient Info
    story.append(section_header("PATIENT INFORMATION"))
    story.append(Spacer(1, 6))
    pi = [
        [Paragraph("<b>Patient Name</b>", styles['FieldLabel']), Paragraph(patient_data.get("patient_name", ""), styles['FieldValue']),
         Paragraph("<b>Date of Birth</b>", styles['FieldLabel']), Paragraph(patient_data.get("dob", ""), styles['FieldValue'])],
        [Paragraph("<b>Patient ID</b>", styles['FieldLabel']), Paragraph(str(patient_data.get("patient_id", "")), styles['FieldValue']),
         Paragraph("<b>Age / Sex</b>", styles['FieldLabel']), Paragraph(f"{patient_data.get('age', '')} / {patient_data.get('sex', '')}", styles['FieldValue'])],
        [Paragraph("<b>Managing Provider</b>", styles['FieldLabel']), Paragraph(patient_data.get("provider", ""), styles['FieldValue']),
         Paragraph("<b>Clinic</b>", styles['FieldLabel']), Paragraph(patient_data.get("clinic_name", ""), styles['FieldValue'])],
    ]
    pt = Table(pi, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    pt.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2), ('BACKGROUND', (0,0), (-1,-1), light_teal), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")), ('LEFTPADDING', (0,0), (-1,-1), 6)]))
    story.append(pt)
    story.append(Spacer(1, 12))

    # Medication
    story.append(section_header("MEDICATION"))
    story.append(Spacer(1, 6))
    mi = [
        [Paragraph("<b>Medication</b>", styles['FieldLabel']), Paragraph(patient_data.get("medication", ""), styles['FieldValue']),
         Paragraph("<b>Indication</b>", styles['FieldLabel']), Paragraph(patient_data.get("indication", ""), styles['FieldValue'])],
        [Paragraph("<b>Dosing</b>", styles['FieldLabel']), Paragraph(patient_data.get("dosing", ""), styles['FieldValue']),
         Paragraph("<b>Start Date</b>", styles['FieldLabel']), Paragraph(patient_data.get("start_date", ""), styles['FieldValue'])],
    ]
    mt = Table(mi, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    mt.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2), ('BACKGROUND', (0,0), (-1,-1), light_teal), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")), ('LEFTPADDING', (0,0), (-1,-1), 6)]))
    story.append(mt)
    story.append(Spacer(1, 12))

    # Screenings
    story.append(section_header("PRE-TREATMENT SCREENING"))
    story.append(Spacer(1, 6))
    sd = [[Paragraph("<b>Screening</b>", styles['FieldLabel']), Paragraph("<b>Date</b>", styles['FieldLabel']), Paragraph("<b>Result</b>", styles['FieldLabel'])]]
    for s in patient_data.get("screenings", []):
        rc = "#155724" if s.get("result") in ("Negative", "Approved", "Within Normal Limits") else "#856404"
        sd.append([Paragraph(s.get("name", ""), styles['FieldValue']), Paragraph(s.get("date", ""), styles['FieldValue']), Paragraph(f"<font color='{rc}'><b>{s.get('result', '')}</b></font>", styles['FieldValue'])])
    st = Table(sd, colWidths=[3.5*inch, 1.5*inch, 2*inch])
    st.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4), ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#D1FAE5")), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")), ('LEFTPADDING', (0,0), (-1,-1), 6), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_teal])]))
    story.append(st)
    story.append(Spacer(1, 12))

    # Appointments
    story.append(section_header("APPOINTMENT SCHEDULE"))
    story.append(Spacer(1, 6))
    ad = [[Paragraph("<b>Visit</b>", styles['FieldLabel']), Paragraph("<b>Date</b>", styles['FieldLabel']), Paragraph("<b>Time</b>", styles['FieldLabel']), Paragraph("<b>Provider</b>", styles['FieldLabel'])]]
    for a in patient_data.get("appointments", []):
        ad.append([Paragraph(a.get("visit", ""), styles['FieldValue']), Paragraph(a.get("date", ""), styles['FieldValue']), Paragraph(a.get("time", ""), styles['FieldValue']), Paragraph(a.get("provider", ""), styles['FieldValue'])])
    at = Table(ad, colWidths=[2.5*inch, 1.5*inch, 1*inch, 2*inch])
    at.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4), ('BACKGROUND', (0,0), (-1,0), teal), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")), ('LEFTPADDING', (0,0), (-1,-1), 6), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_teal])]))
    story.append(at)
    story.append(Spacer(1, 12))

    # Notes
    if patient_data.get("notes"):
        story.append(section_header("CLINICAL NOTES"))
        story.append(Spacer(1, 6))
        nt = Table([[Paragraph(patient_data["notes"], styles['FieldValue'])]], colWidths=[7*inch])
        nt.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FEF3C7")), ('BORDER', (0,0), (-1,-1), 1, colors.HexColor("#F59E0B")), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6), ('LEFTPADDING', (0,0), (-1,-1), 8)]))
        story.append(nt)
        story.append(Spacer(1, 16))

    # Dosing Reference
    story.append(section_header("DOSING SCHEDULE REFERENCE"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(patient_data.get("dosing_schedule", "See prescribing information."), styles['FieldValue']))
    story.append(Spacer(1, 20))

    # Signature
    sig = [
        [Paragraph("_" * 40, styles['FieldValue']), Paragraph("", styles['FieldValue']), Paragraph("_" * 40, styles['FieldValue'])],
        [Paragraph("Provider Signature", styles['FieldLabel']), Paragraph("", styles['FieldValue']), Paragraph("Date", styles['FieldLabel'])],
    ]
    sgt = Table(sig, colWidths=[3*inch, 1*inch, 3*inch])
    sgt.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'BOTTOM'), ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
    story.append(sgt)
    story.append(Spacer(1, 16))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB")))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"CareTopicz Clinical AI Assistant — {patient_data.get('clinic_name', 'Great Clinic')} — "
        "This document is for clinical reference only. All prescribing decisions must be made by the treating clinician.",
        styles['Footer']
    ))

    doc.build(story)
    return output_path
