"""Build resume.pdf from resume.html. Requires Python 3 and reportlab."""
from pathlib import Path
from html.parser import HTMLParser
from html import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

ROOT = Path(__file__).resolve().parents[1]

class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []
    def text(self):
        return ' '.join(''.join(c.text() if isinstance(c, Node) else c for c in self.children).split())
    def findall(self, tag=None, cls=None):
        found = []
        for child in self.children:
            if isinstance(child, Node):
                if (tag is None or child.tag == tag) and (cls is None or cls in child.attrs.get('class','').split()):
                    found.append(child)
                found.extend(child.findall(tag, cls))
        return found

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root')
        self.stack = [self.root]
    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in ('meta','link','img','br','hr','input'):
            self.stack.append(node)
    def handle_endtag(self, tag):
        for idx in range(len(self.stack)-1,0,-1):
            if self.stack[idx].tag == tag:
                self.stack = self.stack[:idx]
                break
    def handle_data(self, data):
        self.stack[-1].children.append(data)

def inline(node, link_color='#7c3aed'):
    chunks = []
    for c in node.children:
        if isinstance(c, str):
            chunks.append(escape(c))
        else:
            text = inline(c, link_color)
            if c.tag == 'a':
                text = f'<a href="{escape(c.attrs["href"],quote=True)}" color="{link_color}">{text}</a>'
            elif c.tag in ('strong','b'):
                text = f'<b>{text}</b>'
            elif c.tag in ('em','i'):
                text = f'<i>{text}</i>'
            chunks.append(text)
    return reflow(''.join(chunks))

def reflow(text):
    return ' '.join(text.split()).replace('\u2013','-').replace('\u2014','-').replace('\u2011','-')

# Embed installed fonts so bold and italic styles survive PDF viewers/renderers.
font_dirs = [
    Path(os.environ.get('RESUME_FONT_DIR', '/System/Library/Fonts/Supplemental')),
    Path('/usr/share/fonts/truetype/msttcorefonts'),
    Path('/usr/share/fonts/truetype/liberation2'),
]
serif, serif_bold, serif_italic, sans_bold = 'Times-Roman', 'Times-Bold', 'Times-Italic', 'Helvetica-Bold'
for folder in font_dirs:
    variants = [
        ('Times New Roman.ttf', 'Times New Roman Bold.ttf', 'Times New Roman Italic.ttf', 'Times New Roman Bold Italic.ttf', 'Arial Bold.ttf'),
        ('LiberationSerif-Regular.ttf', 'LiberationSerif-Bold.ttf', 'LiberationSerif-Italic.ttf', 'LiberationSerif-BoldItalic.ttf', 'LiberationSans-Bold.ttf'),
    ]
    selected = next((v for v in variants if all((folder / f).is_file() for f in v)), None)
    if selected:
        for font_name, filename in zip(('ResumeSerif', 'ResumeSerif-Bold', 'ResumeSerif-Italic', 'ResumeSerif-BoldItalic', 'ResumeSans-Bold'), selected):
            pdfmetrics.registerFont(TTFont(font_name, str(folder / filename)))
        pdfmetrics.registerFontFamily('ResumeSerif', normal='ResumeSerif', bold='ResumeSerif-Bold', italic='ResumeSerif-Italic', boldItalic='ResumeSerif-BoldItalic')
        serif, serif_bold, serif_italic, sans_bold = 'ResumeSerif', 'ResumeSerif-Bold', 'ResumeSerif-Italic', 'ResumeSans-Bold'
        break

accent = HexColor('#7c3aed')
body = ParagraphStyle('Body', fontName=serif, fontSize=10.5, leading=14.7, textColor=HexColor('#111111'))
small = ParagraphStyle('Small', parent=body, fontSize=10.5, leading=14.7)
sub = ParagraphStyle('Sub', parent=body, fontName=serif_italic, fontSize=10.5, leading=14.7)
head = ParagraphStyle('Section', fontName=sans_bold, fontSize=13, leading=17, textColor=accent)
bullet = ParagraphStyle('Bullet', parent=body, leftIndent=15, firstLineIndent=0, bulletIndent=3, spaceAfter=3)
name = ParagraphStyle('Name', fontName=serif_bold, fontSize=28, leading=34, alignment=TA_CENTER, spaceAfter=6)
contact = ParagraphStyle('Contact', parent=small, alignment=TA_CENTER, textColor=HexColor('#475569'))

class SectionHeading(Flowable):
    def __init__(self, title):
        super().__init__()
        self.paragraph = Paragraph(title, head)
        self.height = 26
    def wrap(self, available_width, available_height):
        self.width = available_width
        self.paragraph.wrap(available_width, available_height)
        return self.width, self.height
    def draw(self):
        self.paragraph.drawOn(self.canv, 0, 9)
        self.canv.setStrokeColor(accent)
        self.canv.setLineWidth(0.7)
        self.canv.line(0, 5, self.width, 5)

class TwoColumnRow(Flowable):
    """One aligned row, without table semantics in the resume."""
    def __init__(self, left, right, left_style, right_style=None, left_width=None):
        super().__init__()
        self.left = Paragraph(left, left_style)
        self.right = Paragraph(right, right_style or left_style)
        self.fixed_left_width = left_width
    def wrap(self, available_width, available_height):
        self.width = available_width
        if self.fixed_left_width is not None:
            self.left_width = self.fixed_left_width
            self.right_width = available_width - self.left_width
        else:
            self.right_width = max(self.right.minWidth(), 125)
            self.left_width = available_width - self.right_width - 12
        _, left_height = self.left.wrap(self.left_width, available_height)
        _, right_height = self.right.wrap(self.right_width, available_height)
        self.left_height, self.right_height = left_height, right_height
        self.height = max(left_height, right_height)
        return self.width, self.height
    def draw(self):
        self.left.drawOn(self.canv, 0, self.height - self.left_height)
        self.right.drawOn(self.canv, self.width - self.right_width, self.height - self.right_height)

right_date = ParagraphStyle('RightDate', parent=body, alignment=2)
right_sub = ParagraphStyle('RightSub', parent=sub, alignment=2)

parser = Parser()
parser.feed((ROOT / 'resume.html').read_text())
tree = parser.root
story = [Paragraph(tree.findall('h1')[0].text(), name)]
story.append(Paragraph(inline(tree.findall('p', cls='contact-info')[0], '#475569'), contact))
story.append(Spacer(1, 18))
sections = tree.findall('section')
for section_index, section in enumerate(sections):
    heading = section.findall('h2')[0].text()
    section_heading = SectionHeading(heading)
    items = section.findall('div', cls='cv-item')
    if items:
        for item_index, item in enumerate(items):
            header = item.findall('div', cls='cv-item-header')[0]
            spans = [c for c in header.children if isinstance(c, Node) and c.tag == 'span']
            block = [section_heading] if item_index == 0 else []
            block.append(TwoColumnRow('<b>' + inline(spans[0]) + '</b>', inline(spans[-1]), body, right_date))
            block.append(Spacer(1, 2))
            subtitle = item.findall('div', cls='cv-item-sub')[0]
            fields = [inline(c) for c in subtitle.children if isinstance(c, Node)]
            block.append(TwoColumnRow(fields[0], fields[-1], sub, right_sub))
            block.append(Spacer(1, 4))
            block.extend(Paragraph(inline(li), bullet, bulletText='•') for li in item.findall('li'))
            if item_index < len(items) - 1:
                block.append(Spacer(1, 8))
            story.append(KeepTogether(block))
    else:
        story.append(section_heading)
        for p in section.findall('p'):
            labels = p.findall('strong')
            if labels:
                label = labels[0]
                value_node = Node('span')
                value_node.children = [c for c in p.children if c is not label]
                story.append(TwoColumnRow('<b>' + inline(label) + '</b>', inline(value_node), body, left_width=120))
            else:
                story.append(Paragraph(inline(p), body))
            story.append(Spacer(1, 3))
    if section_index < len(sections) - 1:
        story.append(Spacer(1, 14))

output = ROOT / 'resume.pdf'
doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=18.5*mm, leftMargin=18.5*mm, topMargin=20*mm, bottomMargin=20*mm,
    title='Abdelrahman Elsawy - Resume', author='Abdelrahman Elsawy', subject='Computer Science student focused on AI agents and RAG applications')
doc.build(story)
print(output)
