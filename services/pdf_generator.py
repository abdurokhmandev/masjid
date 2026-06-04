"""
PDF hisobot generatori — reportlab kutubxonasi yordamida.
Foydalanuvchining namoz va qazo statistikasini chiroyli jadvalda taqdim etadi.
"""
import io
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# ──────────────────────────────────────────────
# Ranglar
# ──────────────────────────────────────────────

COLOR_GREEN  = colors.HexColor("#27AE60")
COLOR_RED    = colors.HexColor("#E74C3C")
COLOR_GOLD   = colors.HexColor("#F39C12")
COLOR_DARK   = colors.HexColor("#2C3E50")
COLOR_LIGHT  = colors.HexColor("#ECF0F1")
COLOR_HEADER = colors.HexColor("#1A252F")

PRAYER_DISPLAY = {
    "Fajr":    "🌙 Bomdod",
    "Dhuhr":   "☀️ Peshin",
    "Asr":     "🌤 Asr",
    "Maghrib": "🌆 Shom",
    "Isha":    "🌃 Xufton",
}


def generate_pdf(full_name: str, region: str, stats: dict, logs: list) -> bytes | None:
    """
    Foydalanuvchi statistikasini PDF sifatida generatsiya qiladi.

    :param full_name: Foydalanuvchi to'liq ismi
    :param region: Foydalanuvchi hududi
    :param stats: db.get_qaza_statistics() natijasi
    :param logs: db.get_all_prayer_logs() natijasi ([(date_str, prayer_name, status), ...])
    :return: PDF baytlari yoki None (reportlab yo'q bo'lsa)
    """
    if not REPORTLAB_AVAILABLE:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=20,
        textColor=COLOR_HEADER,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.grey,
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "SectionStyle",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=COLOR_DARK,
        spaceBefore=12,
        spaceAfter=6,
        fontName="Helvetica-Bold",
    )
    normal_style = ParagraphStyle(
        "NormalStyle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=COLOR_DARK,
    )

    story = []
    today = datetime.now().strftime("%d.%m.%Y %H:%M")

    # ─── Sarlavha ──────────────────────────────────────────
    story.append(Paragraph("🕌 Masjidgacha", title_style))
    story.append(Paragraph("Namoz va Qazo Hisoboti", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_GOLD, spaceAfter=8))
    story.append(Paragraph(f"<b>Foydalanuvchi:</b> {full_name}", normal_style))
    story.append(Paragraph(f"<b>Hudud:</b> {region}", normal_style))
    story.append(Paragraph(f"<b>Hisobot sanasi:</b> {today}", normal_style))
    story.append(Spacer(1, 0.4 * cm))

    # ─── Umumiy statistika ─────────────────────────────────
    total_prayed = stats.get("total_prayed", 0)
    total_qaza   = stats.get("total_qaza", 0)
    total_all    = total_prayed + total_qaza
    percent      = int(total_prayed / total_all * 100) if total_all > 0 else 0

    story.append(Paragraph("📊 Umumiy Ko'rsatkichlar", section_style))

    summary_data = [
        ["Ko'rsatkich", "Miqdor"],
        ["✅ O'qilgan namozlar", str(total_prayed)],
        ["❌ Qazo (qoldirilgan) namozlar", str(total_qaza)],
        ["📅 Jami belgilangan", str(total_all)],
        ["📈 O'qish foizi", f"{percent}%"],
    ]
    summary_table = Table(summary_data, colWidths=[10 * cm, 5 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), COLOR_HEADER),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 11),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_LIGHT, colors.white]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE",     (0, 1), (-1, -1), 10),
        ("ROWHEIGHT",    (0, 0), (-1, -1), 22),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.4 * cm))

    # ─── Namoz bo'yicha statistika ─────────────────────────
    story.append(Paragraph("🕌 Namoz Bo'yicha Batafsil", section_style))

    prayer_header = ["Namoz", "✅ O'qilgan", "❌ Qazo", "Jami"]
    prayer_data   = [prayer_header]

    for key, label in PRAYER_DISPLAY.items():
        p_stats  = stats.get(key, {"prayed": 0, "qaza": 0})
        prayed   = p_stats.get("prayed", 0)
        qaza     = p_stats.get("qaza", 0)
        total    = prayed + qaza
        prayer_data.append([label, str(prayed), str(qaza), str(total)])

    prayer_table = Table(prayer_data, colWidths=[6 * cm, 3 * cm, 3 * cm, 3 * cm])
    prayer_table.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), COLOR_DARK),
        ("TEXTCOLOR",      (0, 0), (-1, 0), colors.white),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, 0), 10),
        ("ALIGN",          (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_LIGHT, colors.white]),
        ("GRID",           (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE",       (0, 1), (-1, -1), 10),
        ("ROWHEIGHT",      (0, 0), (-1, -1), 22),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        # O'qilgan ustun — yashil
        ("TEXTCOLOR",      (1, 1), (1, -1), COLOR_GREEN),
        ("FONTNAME",       (1, 1), (1, -1), "Helvetica-Bold"),
        # Qazo ustun — qizil
        ("TEXTCOLOR",      (2, 1), (2, -1), COLOR_RED),
        ("FONTNAME",       (2, 1), (2, -1), "Helvetica-Bold"),
    ]))
    story.append(prayer_table)
    story.append(Spacer(1, 0.4 * cm))

    # ─── So'nggi 30 ta jurnal yozuvi ───────────────────────
    if logs:
        story.append(Paragraph("📋 So'nggi Yozuvlar (oxirgi 30 ta)", section_style))

        log_header = ["Sana", "Namoz", "Holat"]
        log_data   = [log_header]

        STATUS_LABELS = {"prayed": "✅ O'qildi", "qaza": "❌ Qazo", "pending": "⏳ Kutilmoqda"}

        for date_str, prayer_name, status in logs[:30]:
            label = PRAYER_DISPLAY.get(prayer_name, prayer_name)
            # date format: YYYY-MM-DD → DD.MM.YYYY
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
            except Exception:
                d = date_str
            log_data.append([d, label, STATUS_LABELS.get(status, status)])

        log_table = Table(log_data, colWidths=[4 * cm, 6 * cm, 5 * cm])
        log_table.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), COLOR_GOLD),
            ("TEXTCOLOR",      (0, 0), (-1, 0), colors.white),
            ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",       (0, 0), (-1, 0), 9),
            ("ALIGN",          (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_LIGHT, colors.white]),
            ("GRID",           (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ("FONTSIZE",       (0, 1), (-1, -1), 9),
            ("ROWHEIGHT",      (0, 0), (-1, -1), 18),
            ("TOPPADDING",     (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
        ]))
        story.append(log_table)

    # ─── Pastki qism ───────────────────────────────────────
    story.append(Spacer(1, 0.8 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Paragraph(
        "<font color='grey' size='8'>Masjidgacha boti tomonidan avtomatik yaratildi.</font>",
        ParagraphStyle("Footer", parent=styles["Normal"], alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
