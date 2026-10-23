"""Minimal OOXML (.docx) writer and run-level parser. stdlib only.

Writes the smallest .docx that round-trips run formatting properties
(highlight, color, bold, italic, monospace) needed by the experiment.
Parses word/document.xml back into paragraphs -> runs -> (text, cue-set).
"""
import zipfile
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WN = "{%s}" % W

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\
<Default Extension="xml" ContentType="application/xml"/>\
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>\
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\
</Relationships>"""

CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" \
xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>synthetic policy document</dc:title></cp:coreProperties>"""

MONO_FONTS = {"Courier New", "Consolas", "Menlo", "Courier"}


def run_xml(text, cues):
    """One w:r for a sentence. cues: iterable of cue names."""
    props = []
    if "highlight" in cues:
        props.append('<w:highlight w:val="yellow"/>')
    if "color" in cues:
        props.append('<w:color w:val="FF0000"/>')
    if "bold" in cues:
        props.append("<w:b/>")
    if "italic" in cues:
        props.append("<w:i/>")
    if "monospace" in cues:
        props.append('<w:rFonts w:ascii="Courier New" w:hAscii="Courier New"/>')
    rpr = "<w:rPr>%s</w:rPr>" % "".join(props) if props else ""
    return '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, escape(text))


def document_xml(paragraph_runs):
    """paragraph_runs: list of list of (text, cues). One w:p per paragraph."""
    paras = []
    for runs in paragraph_runs:
        paras.append("<w:p>%s</w:p>" % "".join(run_xml(t, c) for t, c in runs))
    body = "".join(paras)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="%s"><w:body>%s'
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/></w:sectPr>'
        "</w:body></w:document>" % (W, body)
    )


def write_docx(path, paragraph_runs):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("docProps/core.xml", CORE)
        z.writestr("word/document.xml", document_xml(paragraph_runs))


def parse_docx(path):
    """Return list of paragraphs; each a list of (text, frozenset(cues))."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    paras = []
    for p in root.iter(WN + "p"):
        runs = []
        for r in p.findall(WN + "r"):
            text = "".join(tn.text or "" for tn in r.findall(WN + "t"))
            cues = set()
            rpr = r.find(WN + "rPr")
            if rpr is not None:
                if rpr.find(WN + "highlight") is not None:
                    cues.add("highlight")
                if rpr.find(WN + "color") is not None:
                    cues.add("color")
                if rpr.find(WN + "b") is not None:
                    cues.add("bold")
                if rpr.find(WN + "i") is not None:
                    cues.add("italic")
                rf = rpr.find(WN + "rFonts")
                if rf is not None and rf.get(WN + "ascii") in MONO_FONTS:
                    cues.add("monospace")
            runs.append((text, frozenset(cues)))
        paras.append(runs)
    return paras
