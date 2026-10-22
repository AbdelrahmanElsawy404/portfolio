"""Build resume.pdf from resume.html. Requires Python 3 and reportlab."""
from pathlib import Path
from html.parser import HTMLParser
from html import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, Flowable
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

def inline(node):
    chunks = []
    for c in node.children:
        if isinstance(c, str):
            chunks.append(escape(c))
        else:
            text = inline(c)
            if c.tag == 'a':
                text = f'<a href="{escape(c.attrs["href"],quote=True)}" color="#475569">{text}</a>'
            elif c.tag in ('strong','b'):
                text = f'<b>{text}</b>'
            elif c.tag in ('em','i'):
                text = f'<i>{text}</i>'
            chunks.append(text)
    return reflow(''.join(chunks))

def reflow(text):
    return ' '.join(text.split()).replace('\u2013','-').replace('\u2014','-').replace('\u2011','-')

accent = HexColor('#7c3aed')
body = ParagraphStyle('Body',fontName='Times-Roman',fontSize=10.5,leading=13.6,textColor=HexColor('#111111'))
small = ParagraphStyle('Small',parent=body,fontSize=9.5,leading=12)
sub = ParagraphStyle('Sub',parent=body,fontName='Times-Italic',fontSize=10,leading=12.8,spaceAfter=3)
head = ParagraphStyle('Section',fontName='Helvetica-Bold',fontSize=11.2,leading=15,textColor=accent,spaceBefore=9,spaceAfter=6,borderColor=accent,borderWidth=0,borderPadding=0)
bullet = ParagraphStyle('Bullet',parent=body,leftIndent=10,firstLineIndent=-8,spaceAfter=3)
name = ParagraphStyle('Name',fontName='Times-Bold',fontSize=25,leading=29,alignment=TA_CENTER,spaceAfter=5)
contact = ParagraphStyle('Contact',parent=small,alignment=TA_CENTER,textColor=HexColor('#475569'),spaceAfter=4)

class ItemHeading(Flowable):
    def __init__(self, title, date):
        super().__init__()
        self.title, self.date = title, reflow(date)
        self.height = 15
    def wrap(self, available_width, available_height):
        self.width = available_width
        return self.width, self.height
    def draw(self):
        self.canv.setFillColor(HexColor('#111111'))
        self.canv.setFont('Times-Bold',10.7)
        self.canv.drawString(0,4,self.title)
        self.canv.setFont('Times-Roman',10)
        self.canv.drawRightString(self.width,4,self.date)

parser = Parser()
parser.feed((ROOT/'resume.html').read_text())
tree = parser.root
story = [Paragraph(tree.findall('h1')[0].text(),name)]
story.append(Paragraph(inline(tree.findall('p',cls='contact-info')[0]),contact))
story.append(Spacer(1,5))
for section in tree.findall('section'):
    heading = section.findall('h2')[0].text()
    story.append(Paragraph(heading,head))
    items = section.findall('div',cls='cv-item')
    if items:
        for item in items:
            header = item.findall('div',cls='cv-item-header')[0]
            spans = [c for c in header.children if isinstance(c,Node) and c.tag=='span']
            block = [ItemHeading(spans[0].text(),spans[-1].text())]
            subtitle = item.findall('div',cls='cv-item-sub')[0]
            fields = [
                f'<a href="{escape(c.attrs["href"], quote=True)}" color="#475569">{inline(c)}</a>'
                if c.tag == 'a' else inline(c)
                for c in subtitle.children if isinstance(c, Node)
            ]
            block.append(Paragraph(' | '.join(fields),sub))
            block.extend(Paragraph('- '+inline(li),bullet) for li in item.findall('li'))
            block.append(Spacer(1,4))
            story.append(KeepTogether(block))
    else:
        for p in section.findall('p'):
            story.append(Paragraph(inline(p),body))
            story.append(Spacer(1,3))

output = ROOT/'resume.pdf'
output.parent.mkdir(parents=True,exist_ok=True)
doc = SimpleDocTemplate(str(output),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=14*mm,bottomMargin=14*mm,
    title='Abdelrahman Elsawy - Resume',author='Abdelrahman Elsawy',subject='Computer Science student focused on AI agents and RAG applications')
doc.build(story)
print(output)
