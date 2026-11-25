#!/usr/bin/env python3
"""Style the report.docx that pandoc wrote: fonts, headings, table borders and shading, captions, header and footer
with page numbers. Called by build_report.py; can also be run alone:  py scripts/style_docx.py report.docx
"""
import copy
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

FONT = "Calibri"
MONO = "Consolas"
INK = RGBColor(0x1F, 0x2A, 0x37)
ACCENT = RGBColor(0x1F, 0x4E, 0x8C)


def set_font(style, name=FONT, size=None, bold=None, italic=None, color=None):
    f = style.font
    f.name = name
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(a), name)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rfonts.get(qn(a)) is not None:
            del rfonts.attrib[qn(a)]
    if size:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if color is not None:
        f.color.rgb = color


def style_by_name(doc, name):
    for s in doc.styles:
        if s.name == name:
            return s
    return None


def shade(cell_or_par_pr, fill):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    cell_or_par_pr.append(shd)


def table_borders(tbl):
    tblPr = tbl._tbl.tblPr
    old = tblPr.find(qn("w:tblBorders"))
    if old is not None:
        tblPr.remove(old)
    b = OxmlElement("w:tblBorders")
    for edge, sz, col in (("top", 8, "7A8794"), ("bottom", 8, "7A8794"), ("insideH", 4, "D0D5DB")):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), col)
        b.append(e)
    tblPr.append(b)
    mar = OxmlElement("w:tblCellMar")
    for edge, w in (("top", 30), ("left", 70), ("bottom", 30), ("right", 70)):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:w"), str(w))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    old = tblPr.find(qn("w:tblCellMar"))
    if old is not None:
        tblPr.remove(old)
    tblPr.append(mar)


GRID_STYLE_ID = "GridTable4-Accent1"


def add_word_table_style(doc):
    """Add Word's built-in "Grid Table 4 - Accent 1" table style (Table Design gallery), so every table uses a
    standard Word style the reader can switch in Word with Table Design > Table Styles."""
    from docx.oxml import parse_xml
    styles = doc.styles.element
    if styles.find(qn("w:style") + "[@" + qn("w:styleId") + "='" + GRID_STYLE_ID + "']") is not None:
        return
    a1, light, band = "4F81BD", "95B3D7", "DBE5F1"
    def border(edge, col=light, themetint=' w:themeTint="99"'):
        return ('<w:%s w:val="single" w:sz="4" w:space="0" w:color="%s" w:themeColor="accent1"%s/>' % (edge, col, themetint))
    outer = "".join(border(e) for e in ("top", "left", "bottom", "right", "insideH", "insideV"))
    head = "".join(border(e, a1, "") for e in ("top", "left", "bottom", "right")) + '<w:insideH w:val="nil"/><w:insideV w:val="nil"/>'
    xml = (
        '<w:style %s w:type="table" w:styleId="%s">'
        '<w:name w:val="Grid Table 4 Accent 1"/><w:uiPriority w:val="49"/><w:qFormat/>'
        '<w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
        '<w:tblPr><w:tblStyleRowBandSize w:val="1"/><w:tblStyleColBandSize w:val="1"/>'
        '<w:tblBorders>%s</w:tblBorders>'
        '<w:tblCellMar><w:top w:w="30" w:type="dxa"/><w:left w:w="70" w:type="dxa"/>'
        '<w:bottom w:w="30" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar></w:tblPr>'
        '<w:tblStylePr w:type="firstRow"><w:rPr><w:b/><w:bCs/><w:color w:val="FFFFFF" w:themeColor="background1"/></w:rPr>'
        '<w:tblPr/><w:tcPr><w:tcBorders>%s</w:tcBorders>'
        '<w:shd w:val="clear" w:color="auto" w:fill="%s" w:themeFill="accent1"/></w:tcPr></w:tblStylePr>'
        '<w:tblStylePr w:type="lastRow"><w:rPr><w:b/><w:bCs/></w:rPr><w:tblPr/><w:tcPr><w:tcBorders>'
        '<w:top w:val="double" w:sz="4" w:space="0" w:color="%s" w:themeColor="accent1"/></w:tcBorders></w:tcPr></w:tblStylePr>'
        '<w:tblStylePr w:type="firstCol"><w:rPr><w:b/><w:bCs/></w:rPr></w:tblStylePr>'
        '<w:tblStylePr w:type="lastCol"><w:rPr><w:b/><w:bCs/></w:rPr></w:tblStylePr>'
        '<w:tblStylePr w:type="band1Vert"><w:tblPr/><w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="%s" w:themeFill="accent1" w:themeFillTint="33"/></w:tcPr></w:tblStylePr>'
        '<w:tblStylePr w:type="band1Horz"><w:tblPr/><w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="%s" w:themeFill="accent1" w:themeFillTint="33"/></w:tcPr></w:tblStylePr>'
        '</w:style>') % ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"', GRID_STYLE_ID,
                         outer, head, a1, a1, band, band)
    styles.append(parse_xml(xml))


def use_word_table_style(tbl):
    """Point the table at the Word style and clear the direct borders and margins so the style shows through."""
    tblPr = tbl._tbl.tblPr
    st = tblPr.find(qn("w:tblStyle"))
    if st is None:
        st = OxmlElement("w:tblStyle")
        tblPr.insert(0, st)
    st.set(qn("w:val"), GRID_STYLE_ID)
    for tag in ("w:tblBorders", "w:tblCellMar"):
        old = tblPr.find(qn(tag))
        if old is not None:
            tblPr.remove(old)
    look = tblPr.find(qn("w:tblLook"))
    if look is None:
        look = OxmlElement("w:tblLook")
        tblPr.append(look)
    for k, v in (("firstRow", "1"), ("lastRow", "0"), ("firstColumn", "0"), ("lastColumn", "0"),
                 ("noHBand", "0"), ("noVBand", "1"), ("val", "04A0")):
        look.set(qn("w:" + k), v)


def field(run, instr):
    for kind, text in (("begin", None), (None, instr), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)


def main(path):
    doc = Document(path)
    st = doc.styles
    for name in ("Normal", "Body Text", "First Paragraph", "Compact", "Block Text"):
        s = style_by_name(doc, name)
        if s is not None:
            set_font(s, size=10.5, color=INK)
            if name in ("Body Text", "First Paragraph"):
                s.paragraph_format.space_after = Pt(6)
                s.paragraph_format.space_before = Pt(0)
                s.paragraph_format.line_spacing = 1.12
    for name, size, before, after in (("Heading 1", 18, 26, 10), ("Heading 2", 13.5, 14, 4), ("Heading 3", 11.5, 10, 3)):
        s = style_by_name(doc, name)
        set_font(s, size=size, bold=True, color=ACCENT)
        s.paragraph_format.space_before = Pt(before)
        s.paragraph_format.space_after = Pt(after)
        s.paragraph_format.keep_with_next = True
    h1 = style_by_name(doc, "Heading 1")
    h1.paragraph_format.page_break_before = False
    h1.paragraph_format.space_before = Pt(26)
    for name, size, bold in (("Title", 26, True), ("Subtitle", 13, False), ("Author", 11, False), ("Date", 11, False)):
        s = style_by_name(doc, name)
        if s is not None:
            set_font(s, size=size, bold=bold, color=INK if name != "Title" else ACCENT)
            s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    t = style_by_name(doc, "Title")
    t.paragraph_format.space_before = Pt(120)
    for name in ("Source Code", "Verbatim Char"):
        s = style_by_name(doc, name)
        if s is not None:
            set_font(s, name=MONO, size=7)
            if name == "Source Code":
                s.paragraph_format.space_after = Pt(0)
                s.paragraph_format.line_spacing = 1.0
                ppr = s.element.get_or_add_pPr()
                shade(ppr, "F3F4F6")
    for name in ("Table Caption", "Figure Caption"):
        s = style_by_name(doc, name)
        if s is not None:
            set_font(s, size=9, color=INK)
            s.paragraph_format.space_before = Pt(8 if name == "Table Caption" else 3)
            s.paragraph_format.space_after = Pt(4 if name == "Table Caption" else 10)
            s.paragraph_format.keep_with_next = name == "Table Caption"
    s = style_by_name(doc, "Contents Heading")
    if s is not None:
        set_font(s, size=18, bold=True, color=ACCENT)
        s.paragraph_format.space_after = Pt(10)
    s = style_by_name(doc, "Contents Entry")
    if s is not None:
        set_font(s, size=11)
        s.paragraph_format.space_after = Pt(3)

    # tables
    add_word_table_style(doc)
    for tbl in doc.tables:
        use_word_table_style(tbl)
        for ri, row in enumerate(tbl.rows):
            trPr = row._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit")
            trPr.append(cs)
            if ri == 0:
                th = OxmlElement("w:tblHeader")
                trPr.append(th)
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.space_after = Pt(0)
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.line_spacing = 1.0
                    for r in p.runs:
                        r.font.size = Pt(8)
                        r.font.name = FONT
                        if ri == 0:
                            r.font.bold = True
    for p in doc.paragraphs:
        if p.style.name == 'Heading 1' and (p.text.startswith('1. ') or p.text.startswith('14. ')):
            p.paragraph_format.page_break_before = True
    body = doc.element.body
    prev_tbl = False
    from docx.text.paragraph import Paragraph
    for child in body.iterchildren():
        if child.tag == qn('w:tbl'):
            prev_tbl = True
        else:
            if prev_tbl and child.tag == qn('w:p'):
                Paragraph(child, doc).paragraph_format.space_before = Pt(8)
            prev_tbl = False
    # image paragraphs
    for p in doc.paragraphs:
        if p._p.xpath(".//w:drawing"):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(6)

    # header and footer
    sec = doc.sections[0]
    for s in doc.sections:
        s.footer.is_linked_to_previous = False
        s.header.is_linked_to_previous = False
        hp = s.header.paragraphs[0] if s.header.paragraphs else s.header.add_paragraph()
        hp.text = ""
        r = hp.add_run("WP3 Technical Report, Evaluation Framework v1.0.0   |   Team P18, ICT30018")
        r.font.size = Pt(8)
        r.font.name = FONT
        r.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)
        fp = s.footer.paragraphs[0] if s.footer.paragraphs else s.footer.add_paragraph()
        fp.text = ""
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run()
        r.font.size = Pt(9)
        r.font.name = FONT
        field(r, "PAGE")
    doc.core_properties.title = "WP3 Technical Report: Evaluation Framework and Metrics"
    doc.core_properties.author = "Team P18 (WP3)"
    doc.save(path)


if __name__ == "__main__":
    main(sys.argv[1])
