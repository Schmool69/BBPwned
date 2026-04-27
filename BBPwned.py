from tkinter import *
from tkinter import font, messagebox, filedialog
from tkinterweb import HtmlFrame
import webbrowser
import tempfile
from customtkinter import *
from playwright.sync_api import sync_playwright
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import requests, json, warnings, urllib.request, tempfile, os, re
from urllib.parse import urlparse
from urllib.parse import parse_qs
from urllib.parse import urlencode
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from queue import Queue
import threading
from datetime import datetime
import pickle
import base64
from PyPDF2 import PdfReader
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def h1RequestOne(handle):
    if handle == "acunetix":
        goList = ["Acunetix Test Site", "testphp.vulnweb.com", "testhtml5.vulnweb.com", "testasp.vulnweb.com", "testaspnet.vulnweb.com", "rest.vulnweb.com"]
        return goList
    url = "https://api.hackerone.com/v1/hackers/programs/" + handle
    login = ('HACKERONE_USERNAME', 'HACKERONE_API_KEY')
    accepts = { 'Accept': 'application/json' }
    data = requests.get(url, headers=accepts, auth=login)
    finalJson = json.loads(data.text)
    goList = []
    goList.append(finalJson['attributes']['name'])
    for relationship in finalJson['relationships']['structured_scopes']['data']:
        if relationship['attributes']['eligible_for_bounty'] and (relationship['attributes']['asset_type'] == "URL" or relationship['attributes']['asset_type'] == "Domain"):
            goList.append(relationship['attributes']['asset_identifier'])
    return goList

def openCrawlPage(link, app, isNewCrawl):
    if isNewCrawl:
        app.visitedUrls = []
        app.urlTree = {}
        app.urlsWithForms = set()
        app.urlsWithQueryParams = set()
        app.crawledScopes.add(link) if link not in app.crawledScopes else None
    loadingFrame = CTkFrame(app.base)
    loadingFrame.grid(row=0, column=0, sticky="nsew")
    loadingLabel = CTkLabel(loadingFrame, text="Crawling URLs (establishing connection)...")
    loadingLabel.pack(pady=20)
    progressBar = CTkProgressBar(loadingFrame, orientation="horizontal", width=300)
    progressBar.pack(pady=10)
    progressBar.set(0)
    app.cancelled = False
    cancelButton = CTkButton(loadingFrame, text="Cancel", command=lambda: app.cancel())
    cancelButton.pack(pady=10)
    app.update()
    app.makeFrame(CrawlListPage, link, loadingFrame, progressBar, loadingLabel, isNewCrawl)
    app.showFrame("CrawlListPage") if not app.cancelled else None

class Menubar(CTk):
    def __init__(self, parent):
        self.menu = Menu(parent)
        file = Menu(self.menu, tearoff=0)
        tools = Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="File", menu=file)
        file.add_command(label="New Project", command=lambda: parent.restart())
        file.add_command(label="Save Report", command=lambda: parent.saveProject())
        self.menu.add_cascade(label="tools", menu=tools)
        tools.add_command(label="Scope List", command=lambda: parent.returnToScopeList())
        tools.add_command(label="Crawl Tree", command=lambda: parent.showFrame("CrawlListPage"))

class App(CTk):
    def __init__(self, *args, **kwargs):
        CTk.__init__(self, *args, **kwargs)
        self.title("BBPwned")
        self.foundHandle = True
        self.menubar = Menubar(self).menu
        self.config(menu="")
        self.geometry("1200x700")
        self.base = CTkFrame(self)
        self.base.pack(fill="both", expand=True)
        self.base.rowconfigure(0, weight=1)
        self.base.columnconfigure(0, weight=1)
        self.frames = {}
        self.goList = []
        self.PDF = None
        self.crawledScopes = set()
        self.insecureProtocol = False
        self.faultyLink = False
        self.selectedScope = None
        self.programName = None
        self.testResults = {}
        self.makeFrame(StartPage)
        self.showFrame("StartPage")

    def restart(self):
        self.insecureProtocol = False
        self.faultyLink = False
        self.showFrame("StartPage")
        self.PDF = None
        self.selectedScope = None
        self.programName = None
        self.testResults = {}
        self.visitedUrls = []
        self.urlTree = {}
        self.urlsWithForms = set()
        self.urlsWithQueryParams = set()

    def saveProject(self):
        if not self.selectedScope:
            messagebox.showerror("Error", "Please crawl a scope before saving the project.")
            return
        
        filePath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=f"{self.programName or 'project'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        
        if not filePath:
            return
        
        try:

            doc = SimpleDocTemplate(filePath, pagesize=letter)
            contentList = []
            styles = getSampleStyleSheet()
            
            titleStyle = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#0066cc'),
                spaceAfter=30,
                alignment=1
            )
            contentList.append(Paragraph(f"<b>BBPwned - Bug Bounty Report</b>", titleStyle))
            contentList.append(Spacer(1, 0.3*inch))
            
            programStyle = ParagraphStyle(
                'ProgramInfo',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#333333'),
                spaceAfter=6
            )
            contentList.append(Paragraph(f"<b>Program Name:</b> {self.programName}", programStyle))
            contentList.append(Paragraph(f"<b>Report Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", programStyle))
            contentList.append(Spacer(1, 0.2*inch))
            
            contentList.append(Paragraph("<b>Crawled Scopes</b>", styles['Heading2']))
            scopeList = [['Domain']]
            domainList = set()
            for url in self.crawledScopes:
                scopeList.append([url])
            
            if len(scopeList) > 1:
                scopeTable = Table(scopeList, colWidths=[5*inch])
                scopeTable.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                contentList.append(scopeTable)
            contentList.append(Spacer(1, 0.2*inch))
            
            contentList.append(Paragraph("<b>Tested Pages and Results</b>", styles['Heading2']))
            contentList.append(Spacer(1, 0.1*inch))
            
            if self.testResults:
                urlStyle = ParagraphStyle(
                    'URLStyle',
                    parent=styles['Normal'],
                    fontSize=10,
                    textColor=colors.HexColor('#0066cc'),
                    spaceAfter=3,
                    leftIndent=10
                )
                resultStyle = ParagraphStyle(
                    'ResultStyle',
                    parent=styles['Normal'],
                    fontSize=9,
                    textColor=colors.HexColor('#333333'),
                    spaceAfter=8,
                    leftIndent=20
                )
                
                for url in sorted(self.testResults.keys()):
                    testResults = self.testResults[url]
                    hasForm = testResults.get('hasForm', False)
                    hasQuery = testResults.get('hasQuery', False)
                    
                    indicators = []
                    if hasForm:
                        indicators.append("📋 Forms")
                    if hasQuery:
                        indicators.append("? Query Params")
                    indicatorText = " | ".join(indicators) if indicators else "Static"
                    contentList.append(Paragraph(f"<b>{url}</b><br/><i>{indicatorText}</i>", urlStyle))
                    vulnText = "<b>Vulnerabilities Found:</b><br/>"
                    for testName, testValue in testResults.items():
                        if testName != 'hasForm' and testName != 'hasQuery' and testValue['result'] == True:
                            vulnText = vulnText + f"{testName}<br/>&nbsp;&nbsp;&nbsp;&nbsp;{testValue['reason']}<br/>"
                            
                    contentList.append(Paragraph(vulnText, resultStyle)) if vulnText != "<b>Vulnerabilities Found:</b><br/>" else contentList.append(Paragraph("No vulnerabilities found on tested page.", resultStyle))
                    contentList.append(Spacer(1, 0.05*inch))
            else:
                contentList.append(Paragraph("No pages have been tested.", styles['Normal']))
            
            doc.build(contentList)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project:\n{str(e)}")
            print(f"Error saving project: {e}")

    def makeFrame(self, F, *args):
        pageName = F.__name__
        newFrame = F(self.base, self, *args)
        self.frames[pageName] = newFrame
        newFrame.grid(row=0, column=0, sticky="nsew")
    
    def showFrame(self, pageName):
        try:
            frame = self.frames[pageName]
        except:
            print(f"Frame {pageName} does not exist.")
            return

        for f in self.frames.values():
            self.disableFrame(f)

        self.enableFrame(frame)
        print(f"Showing frame: {pageName}")
        frame.tkraise()
        
        if pageName == "StartPage":
            self.config(menu="")
    
    def disableFrame(self, frame):
        for child in frame.winfo_children():
            if isinstance(child, CTkButton) or isinstance(child, CTkEntry) or isinstance(child, CTkSlider):
                child.configure(state="disabled")
            elif isinstance(child, CTkFrame) or isinstance(child, CTkScrollableFrame):
                self.disableFrame(child)
    
    def enableFrame(self, frame):
        for child in frame.winfo_children():
            if isinstance(child, CTkButton) or isinstance(child, CTkEntry) or isinstance(child, CTkSlider):
                child.configure(state="normal")
            elif isinstance(child, CTkFrame) or isinstance(child, CTkScrollableFrame):
                self.enableFrame(child)

    def searchHandle(self, handle, source):
        try:
            self.goList = h1RequestOne(handle)
        except Exception as E:
            print(E)
            source.errorMessage.pack()
            source.handleInput.delete(0, END)
            return
        source.handleInput.delete(0, END)
        self.makeFrame(ScopeListPage, self.goList)
        self.showFrame("ScopeListPage")
        self.config(menu=self.menubar)

    def cancel(self):
        self.cancelled = True
    
    def returnToScopeList(self):
        self.faultyLink = False
        self.showFrame("ScopeListPage")

class StartPage(CTkFrame):
    def __init__(self, parent, app):
        CTkFrame.__init__(self, parent)
        self.innerFrame = CTkFrame(self, fg_color="transparent")
        self.innerFrame.place(relx=0.5, rely=0.4, anchor="center")
        title_frame = CTkFrame(self.innerFrame, fg_color="transparent")
        title_frame.pack(pady=(0, 30))
        CTkLabel(title_frame, text="BBPwned", 
                font=("Arial", 48, "bold")).pack()
        CTkLabel(title_frame, text="Bug Bounty Program Scanner",
                font=("Arial", 14),
                text_color=("gray60", "gray45")).pack()
        input_frame = CTkFrame(self.innerFrame, fg_color="transparent")
        input_frame.pack(fill="x", padx=20)
        CTkLabel(input_frame, text="Enter BBP Handle",
                font=("Arial", 14)).pack(pady=(0, 5))
        search_frame = CTkFrame(input_frame, fg_color="transparent")
        search_frame.pack(fill="x")
        self.handleInput = CTkEntry(search_frame, width=240,
                                  placeholder_text="program-handle")
        self.handleInput.pack(side="left", padx=(0, 10))
        
        submitButton = CTkButton(search_frame, text="Search", width=100,
                               command=lambda: app.searchHandle(self.handleInput.get(), self))
        submitButton.pack(side="left")
        self.errorMessage = CTkLabel(input_frame, text="Error: BBP not found",
                                   text_color="red") 
        app.bind('<Return>', lambda x: app.searchHandle(self.handleInput.get(), self))
        
class ScopeListPage(CTkFrame):
    def __init__(self, parent, app, goList):
        CTkFrame.__init__(self, parent)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        headerFrame = CTkFrame(self, fg_color="transparent")
        headerFrame.grid(row=0, column=0, pady=(30, 0), sticky="ew")
        if not app.programName:
            app.programName = goList.pop(0)
        programNameText = app.programName
        app.programName = programNameText
        programName = CTkLabel(headerFrame, 
                              text=programNameText,
                              font=("Arial", 32, "bold"))
        programName.pack()
        
        subtitleFrame = CTkFrame(self, fg_color="transparent")
        subtitleFrame.grid(row=1, column=0, pady=(5, 20), sticky="ew")
        CTkLabel(subtitleFrame,
                text="Select a domain from the program scope to begin crawling",
                font=("Arial", 14),
                text_color=("gray60", "gray45")).pack()
        
        contentFrame = CTkFrame(self, fg_color="transparent")
        contentFrame.grid(row=2, column=0, sticky="nsew", padx=40)
        contentFrame.grid_columnconfigure(0, weight=1)
        
        selectFrame = CTkFrame(contentFrame, fg_color=("gray95", "gray20"))
        selectFrame.pack(fill="x", pady=20, ipady=20)
        
        CTkLabel(selectFrame,
                text="Available Scope Domains",
                font=("Arial", 14, "bold")).pack(pady=(10, 5))
        
        choice = CTkOptionMenu(selectFrame,
                             values=goList,
                             width=400,
                             dynamic_resizing=False)
        choice.pack(pady=10)
        
        sliderFrame = CTkFrame(selectFrame, fg_color="transparent")
        sliderFrame.pack(pady=(20, 10), padx=40)
        
        CTkLabel(sliderFrame, text="Crawl Depth", font=("Arial", 12)).pack()
        
        self.depthSlider = CTkSlider(sliderFrame, 
                                    from_=0, 
                                    to=2,
                                    number_of_steps=2,
                                    width=300)
        self.depthSlider.pack(pady=5)
        
        labelsFrame = CTkFrame(sliderFrame, fg_color="transparent")
        labelsFrame.pack(fill="x")
        
        app.depth = 500

        CTkLabel(labelsFrame, text="Light", font=("Arial", 10)).pack(side="left", expand=True)
        CTkLabel(labelsFrame, text="Medium", font=("Arial", 10)).pack(side="left", expand=True)
        CTkLabel(labelsFrame, text="Deep", font=("Arial", 10)).pack(side="left", expand=True)
        
        self.warningLabel = CTkLabel(sliderFrame, 
                                    text="⚠️ Deep crawl may take significantly longer",
                                    text_color="orange",
                                    font=("Arial", 11))
        
        def onSliderChange(value):
            match value:
                case 0:
                    app.depth = 100
                    self.warningLabel.pack_forget()
                case 1:
                    app.depth = 500
                    self.warningLabel.pack_forget()
                case 2:
                    app.depth = 1000
                    self.warningLabel.pack(pady=(10, 0))
        
        self.depthSlider.configure(command=onSliderChange)
        
        strategyFrame = CTkFrame(selectFrame, fg_color="transparent")
        strategyFrame.pack(pady=(20, 0))
        
        CTkLabel(strategyFrame, text="Crawl Strategy", font=("Arial", 12)).pack()
        
        app.crawlStrategy = "breadth-first"
        
        def switchEvent():
            app.crawlStrategy = "depth-first" if strategySwitch.get() == 1 else "breadth-first"
            
        strategySwitch = CTkSwitch(strategyFrame, 
                                  text="", 
                                  command=switchEvent,
                                  width=60)
        strategySwitch.pack(pady=5, padx=(27, 0))

        switchLabels = CTkFrame(strategyFrame, fg_color="transparent")
        switchLabels.pack(fill="x", pady=(0, 10))
        
        CTkLabel(switchLabels, text="Breadth-first", font=("Arial", 10)).pack(side="left", padx=10)
        CTkLabel(switchLabels, text="Depth-first", font=("Arial", 10)).pack(side="right", padx=10)
        
        CTkButton(selectFrame,
                 text="Start Crawling",
                 font=("Arial", 13),
                 width=200,
                 height=35,
                 command=lambda: [setattr(app, 'selectedScope', choice.get()), openCrawlPage(choice.get(), app, True)]).pack(pady=20)

class CrawlListPage(CTkFrame):
    def __init__(self, parent, app, link, loadingFrame, progressBar, loadingLabel, isNewCrawl):
        self.queryUrls = set()
        self.formUrls = set()
        self.urlList = []
        CTkFrame.__init__(self, parent)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.loadingFrame = loadingFrame
        self.progressBar = progressBar
        self.loadingLabel = loadingLabel
        self.urlCrawl(link, app)
        if app.cancelled:
            print("cancelled")
            if isNewCrawl:
                app.showFrame("ScopeListPage")
                self.loadingFrame.destroy()
                return
            self.loadingFrame.destroy()
        mainContainer = CTkFrame(self)
        mainContainer.grid(row=0, column=0, sticky="nsew")
        mainContainer.grid_rowconfigure(1, weight=1)
        mainContainer.grid_columnconfigure(0, weight=1)
        mainContainer.grid_rowconfigure(1, weight=1)
        header = CTkLabel(mainContainer, text="URL Directory Tree", font=("Arial", 16, "bold"))
        header.grid(row=0, column=0, pady=10, padx=5, sticky="w")
        self.treeFrame = CTkScrollableFrame(mainContainer)
        self.optionsFrame = CTkFrame(mainContainer, fg_color="transparent")
        self.optionsFrame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=5, pady=5)
        CTkLabel(self.optionsFrame, text="Options", font=("Arial", 16, "bold")).pack(pady=10)
        if app.insecureProtocol:
            CTkLabel(self.optionsFrame, text="Note: Insecure protocol detected,\none or more links used http over https", text_color="red").pack(pady=5)
        self.crawlFurtherButton = CTkButton(self.optionsFrame, text="Crawl Further", command=lambda: self.recrawl(app))
        self.crawlFurtherButton.pack(pady=5, padx=5)
        self.renderButton = CTkButton(self.optionsFrame, text="Render Page", command=lambda: renderLink(app, self.activeLink))
        self.renderButton.pack(pady=5, padx=5)
        self.testButton = CTkButton(self.optionsFrame, text="Test Page", command=lambda: testLink(app, self.activeLink))
        self.testButton.pack(pady=5, padx=5)
        self.treeKey = CTkLabel(self.optionsFrame, text="Key:\n📋 - Page contains forms\n? - Page contains query parameters\n?📋 - page contains both", font=("Arial", 12), justify="left")
        self.treeKey.pack(pady=10, padx=5, side="bottom")
        self.treeFrame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        if app.faultyLink:
            CTkLabel(self.treeFrame, text="Chosen domain is down or inaccessible,\n try a different domain or retry later", text_color="red").pack(pady=5)
        self.buildTree(app=app)
        self.activeLink = app.visitedUrls[0] if app.visitedUrls else None
        if not self.activeLink:
            self.crawlFurtherButton.configure(state="disabled")
            self.renderButton.configure(state="disabled")
            self.testButton.configure(state="disabled")
        self.loadingFrame.destroy()

    def recrawl(self, app):
        app.depth = 100
        app.crawlStrategy = "breadth-first"
        openCrawlPage(self.activeLink, app, False)
        
    def setActiveLink(self, urlKey):
        self.activeLink = urlKey
        print(f"Set active link to: {self.activeLink}")

    def addTree(self, url, app):
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        currentDict = app.urlTree
        if parsed.netloc not in currentDict:
            currentDict[parsed.netloc] = {}
            currentDict[parsed.netloc]["url"] = url
        currentDict = currentDict[parsed.netloc]
        for part in path_parts:
            if part not in currentDict:
                currentDict[part] = {}
                currentDict[part]["url"] = url
            currentDict = currentDict[part]
    
    def buildTree(self, app, parentFrame=None, treeDict=None, indent=0):
        if parentFrame is None:
            parentFrame = self.treeFrame
        if treeDict is None:
            treeDict = app.urlTree
        for key, value in sorted(treeDict.items()):
            if key == "url":
                continue
                
            rowFrame = CTkFrame(parentFrame, fg_color="transparent")
            rowFrame.pack(fill="x", pady=2)
            
            treeLine = "└── " if indent > 0 else ""
            if indent > 1:
                treeLine = "│   " * (indent-1) + treeLine
            
            url = value.get("url", "")
            hasForm = url in app.urlsWithForms
            hasQuery = url in app.urlsWithQueryParams
            btnText = treeLine + key

            if hasForm:
                btnText = "📋 " + btnText
            if hasQuery:
                btnText = "?" + btnText

            if hasForm:
                btnColour = "#1f6aa5"
                btnHover = "#2e8bc0"
                btnTextColour = "white"
            elif hasQuery:
                btnColour = "#2d8659"
                btnHover = "#3da66f"
                btnTextColour = "white"
            else:
                btnColour = "transparent"
                btnHover = ("gray85", "gray25")
                btnTextColour = None
                
            btn = CTkButton(rowFrame, text=btnText, command=lambda value=value: self.setActiveLink(value["url"]), font=("Consolas", 12), fg_color=btnColour, hover_color=btnHover, anchor="w", height=22, text_color=btnTextColour)
            btn.pack(side="left", padx=(indent*10, 5), fill="x")
            if isinstance(value, dict):
                self.buildTree(app, parentFrame, value, indent + 1)
    
    def refreshTree(self, app):
        for widget in self.treeFrame.winfo_children():
            widget.destroy()
        self.buildTree(app=app)

    def urlCrawl(self, link, app):
        if not link.startswith("http"):
            try:
                requests.get("https://" + link, timeout=5)
                link = "https://" + link
            except:
                try:
                    requests.get("http://" + link, timeout=5)
                    link = "http://" + link
                    app.insecureProtocol = True
                except:
                    app.faultyLink = True
                    return
        if not link == "":
            self.urlList.append(link)
        count = 0
        failCount = 0
        stopTracking = False
        while self.urlList and count < app.depth:
            if app.cancelled:
                return
            if count + len(self.urlList) > app.depth:
                removedUrls = self.urlList[app.depth - count:]
                self.urlList = self.urlList[:app.depth - count]
                stopTracking = True
                for removedUrl in removedUrls:
                    app.visitedUrls.remove(removedUrl)
            with ThreadPoolExecutor(max_workers=16) as executor:
                newLinks = {executor.submit(requests.get, newLink, timeout=5): newLink for newLink in self.urlList}
                for newLink in concurrent.futures.as_completed(newLinks):
                    print(f"Crawled: {newLinks[newLink]}")
                    self.progressBar.set(count/app.depth)
                    self.loadingLabel.configure(text=f"Crawling URLs ({count}/{app.depth} requests)...")
                    app.update()
                    if app.cancelled:
                        return
                    self.urlList.remove(newLinks[newLink])
                    try:
                        page = newLink.result()
                    except:
                        failCount += 1
                        if failCount > 10:
                            return
                        continue
                    if urlparse(page.url).netloc not in app.goList:
                        continue
                    newLinks[newLink] = page.url
                    failCount = 0
                    parsedUrl = urlparse(newLinks[newLink])
                    capturedValues = parse_qs(parsedUrl.query)
                    if parsedUrl.query:
                        app.urlsWithQueryParams.add(newLinks[newLink])
                    capturedValues = {val: "1" for val in capturedValues}
                    self.addTree(newLinks[newLink], app)
                    soup = BeautifulSoup(page.text, "html.parser")
                    links = soup.select("a[href]")
                    forms = soup.select("form")
                    if stopTracking == False:
                        for form in forms:
                            app.urlsWithForms.add(newLinks[newLink])
                        for link in links:
                            url = link['href']
                            if not url.startswith("#") and (not url.startswith("http")) and not url.startswith("mailto"):
                                url = requests.compat.urljoin(newLinks[newLink], url)
                                if url in app.visitedUrls:
                                    continue
                                if app.crawlStrategy == "depth-first":
                                    self.urlList.insert(0, url)
                                    app.visitedUrls.insert(0, url)
                                else:
                                    self.urlList.append(url)
                                    app.visitedUrls.append(url)
                            else:
                                continue
                    count += 1

def testLink(app, activeLink):
    print(f"Testing page for: {activeLink}")
    loadingFrame = CTkFrame(app.base)
    loadingFrame.grid(row=0, column=0, sticky="nsew")
    loadingLabel = CTkLabel(loadingFrame, text="Extracting forms and query parameters...")
    loadingLabel.pack(pady=20)
    app.update()
    formData = []
    queryParams = {}
    
    try:
        response = requests.get(activeLink, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")

        forms = soup.select("form")
        for form in forms:
            formInfo = {
                'method': form.get('method', 'POST').upper(),
                'action': form.get('action', activeLink),
                'inputs': []
            }
            if not formInfo['action'].startswith('http'):
                formInfo['action'] = requests.compat.urljoin(activeLink, formInfo['action'])
            
            for input_field in form.select("input, textarea, select"):
                fieldInfo = {
                    'name': input_field.get('name', ''),
                    'type': input_field.get('type', 'text'),
                    'value': input_field.get('value', ''),
                    'tag': input_field.name
                }
                formInfo['inputs'].append(fieldInfo)
            
            if formInfo['inputs']:
                formData.append(formInfo)
        
        parsed_url = urlparse(activeLink)
        if parsed_url.query:
            queryParams = parse_qs(parsed_url.query)
    except Exception as e:
        print(f"Error extracting forms: {e}")
    
    app.makeFrame(TestPage, activeLink, formData, queryParams, loadingLabel)
    app.showFrame("TestPage")
    loadingFrame.destroy()

class TestPage(CTkFrame):
    def __init__(self, parent, app, activeLink, formData, queryParams, loadingLabel):
        CTkFrame.__init__(self, parent)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_propagate(False)

        self.app = app
        self.activeLink = activeLink
        self.formData = formData
        self.queryParams = queryParams
        self.lastResponse = None
        self.lastResponseHeaders = {}
        self.pageTestResults = {}
        self.autoTested = False

        header = CTkLabel(self, text=f"Test Page - {activeLink}", font=("Arial", 16, "bold"))
        header.grid(row=0, column=0, pady=10, padx=10, columnspan=2, sticky="w")
        
        buttonFrame = CTkFrame(self, fg_color="transparent")
        buttonFrame.grid(row=0, column=1, sticky="e", padx=10, pady=10)

        returnButton = CTkButton(buttonFrame, text="Return to Crawl Tree", command=lambda: app.showFrame("CrawlListPage"))
        returnButton.pack(side="left", padx=5)
        
        sendButton = CTkButton(buttonFrame, text="Send Request", command=lambda: self.sendRequest())
        sendButton.pack(side="left", padx=5)

        reportButton = CTkButton(buttonFrame, text="Add to Report", command=lambda: self.addToReport(app))
        reportButton.pack(side="left", padx=5)

        self.pageButton = CTkButton(buttonFrame, text="View Page", command=lambda: self.swapView(app))
        self.pageButton.pack(side="left", padx=5)

        self.autoTestButton = CTkButton(buttonFrame, text="Auto-Test with Payloads", command=lambda: self.autoTest(app))
        self.autoTestButton.pack(side="left", padx=5)

        requestFrame = CTkScrollableFrame(self)
        requestFrame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        CTkLabel(requestFrame, text="HTTP Request", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        methodFrame = CTkFrame(requestFrame, fg_color="transparent")
        methodFrame.pack(fill="x", padx=10, pady=5)
        CTkLabel(methodFrame, text="Method:", font=("Arial", 10)).pack(side="left", padx=(0, 10))
        self.methodVar = StringVar(value="GET")
        self.methodMenu = CTkComboBox(methodFrame, values=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"], variable=self.methodVar, width=80)
        self.methodMenu.pack(side="left")
        
        CTkLabel(requestFrame, text="URL:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.urlEntry = CTkTextbox(requestFrame, height=60, width=300)
        self.urlEntry.pack(fill="x", padx=10, pady=5)
        self.urlEntry.insert("1.0", activeLink)

        CTkLabel(requestFrame, text="Parameters:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.paramsEntry = CTkTextbox(requestFrame, height=100, width=300)
        self.paramsEntry.pack(fill="x", padx=10, pady=5)
        self.paramsEntry.insert("1.0", "param1=value1&param2=value2")
        
        CTkLabel(requestFrame, text="Headers:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.headersEntry = CTkTextbox(requestFrame, height=100, width=300)
        self.headersEntry.pack(fill="x", padx=10, pady=5)
        self.headersEntry.insert("1.0", "Content-Type: application/x-www-form-urlencoded\nUser-Agent: Mozilla/5.0")
        
        CTkLabel(requestFrame, text="Body:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.bodyEntry = CTkTextbox(requestFrame, height=100, width=300)
        self.bodyEntry.pack(fill="both", padx=10, pady=5)
        
        if formData:
            self.populateFromForm(formData[0])
        else:
            self.bodyEntry.delete("1.0", END)
            self.bodyEntry.insert("1.0", "No forms detected on this page.")
            self.bodyEntry.configure(state="disabled")
        if queryParams:
            self.populateFromQueryParams()
        else:
            self.paramsEntry.delete("1.0", END)
            self.paramsEntry.insert("1.0", "No query parameters detected on this page.")
            self.paramsEntry.configure(state="disabled")
        
        self.responseFrame = CTkScrollableFrame(self)
        self.responseFrame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        CTkLabel(self.responseFrame, text="Response", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.statusLabel = CTkLabel(self.responseFrame, text="Status: Awaiting request...", font=("Consolas", 9))
        self.statusLabel.pack(anchor="w", padx=10, pady=2)

        CTkLabel(self.responseFrame, text="Response Headers:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.responseHeadersText = CTkTextbox(self.responseFrame, height=200, width=300)
        self.responseHeadersText.pack(fill="x", padx=10, pady=5)
        self.responseHeadersText.configure(state="disabled")
        
        CTkLabel(self.responseFrame, text="Response Body:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.responseBodyText = CTkTextbox(self.responseFrame, height=500, width=300)
        self.responseBodyText.pack(fill="both", expand=True, padx=10, pady=5)
        self.responseBodyText.configure(state="disabled")

        self.pageFrame = HtmlFrame(self, horizontal_scrollbar="auto", messages_enabled=False)
        self.pageFrame.load_html("Awaiting Request...")

        self.autoResultsFrame = CTkScrollableFrame(self)            

        loadingLabel.pack_forget()

    def autoTest(self, app):
        if self.autoResultsFrame.winfo_ismapped():
            self.autoResultsFrame.grid_remove()
            self.responseFrame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
            self.autoTestButton.configure(text="Test Results")
        else:
            self.autoResultsFrame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
            self.responseFrame.grid_remove()
            self.autoTestButton.configure(text="Return")
            
            if not self.autoTested:
                self.runFormTests()
                self.runQueryParameterTests()
                app.testResults[self.activeLink] = self.pageTestResults
                self.autoTested = True

    def calculateSimilarity(self, text1, text2):
        len1, len2 = len(text1), len(text2)
        if len1 == 0 and len2 == 0:
            return 1.0
        if len1 == 0 or len2 == 0:
            return 0.0

        matchingChars = sum(c1 == c2 for c1, c2 in zip(text1, text2))
        lengthDiff = abs(len1 - len2) / max(len1, len2)
        similarity = matchingChars / max(len1, len2)
        
        return (similarity + (1 - lengthDiff)) / 2
    
    def detectSQLErrors(self, responseText):
        patterns = [
            r"(?i)(sql syntax|sql error|MySQL Error|MariaDB|PostgreSQL|ORA-\d+|SQLServer|ODBC|JDBC)",
            r"(?i)(syntax error|unexpected end|column count|table .* doesn)",
            r"(?i)(You have an error|Warning: mysql|Fatal error|Unknown column)",
            r"(?i)(SQLSTATE|driver\]:|Exception)",
        ]
        for pattern in patterns:
            if re.search(pattern, responseText):
                return True
        return False
    
    def detectOpenRedirect(self, response, testUrl):
        if 'location' in response.headers or 'Location' in response.headers:
            redirectUrl = response.headers.get('location') or response.headers.get('Location', '')
            if testUrl in redirectUrl:
                return True, redirectUrl
        if response.status_code in [301, 302, 303, 307, 308]:
            return True, response.headers.get('Location', 'Unknown redirect')
        return False, None
    
    def detectPathTraversal(self, responseText):
        patterns = [
            r"root:",
            r"bin/bash",
            r"/etc/passwd",
            r"rwx",
            r"drwx",
        ]
        for pattern in patterns:
            if re.search(pattern, responseText):
                return True
        return False
    
    def detectLDAPInjection(self, responseText):
        patterns = [
            r"(?i)(ldap|directory)",
            r"(?i)(authentication failed|invalid query)",
        ]
        for pattern in patterns:
            if re.search(pattern, responseText):
                return True
        return False
    
    def detectParameterPollution(self, responseText, statusCode, CStatusCode, testValue=None):
        errorPatterns = [
            r"(?i)(duplicate|multiple|repeated|duplicate.*param|param.*duplicate)",
            r"(?i)(invalid.*request|bad.*request|malformed)",
            r"(?i)(unexpected.*parameter|unknown.*parameter)",
            r"(?i)(400|403|422)",
        ]
        
        if statusCode != CStatusCode and statusCode >= 400:
            return True
        
        for pattern in errorPatterns:
            if re.search(pattern, responseText):
                return True
        
        if testValue and testValue in responseText:
            return True
        
        return False

    def runQueryParameterTests(self):
        if not self.queryParams:
            return
        
        resultsLabel = CTkLabel(self.autoResultsFrame, text="Query Parameter Tests", font=("Arial", 11, "bold"), text_color="#aaff44")
        resultsLabel.pack(anchor="w", padx=10, pady=(20, 5))
        
        originalParams = {k: v[0] if v else "" for k, v in self.queryParams.items()}
        sqlPayloads = {k: "' OR 1=1 " for k in originalParams}
        xssPayloads = {k: "<script>alert(1)</script>" for k in originalParams}
        controlParams1 = {k: f"{v}_1" for k, v in originalParams.items()}
        controlParams2 = {k: f"{v}_2" for k, v in originalParams.items()}
        pollutionParams = {}
        
        for key in originalParams:
            pollutionParams[key] = originalParams[key]
            pollutionParams[key + "_dup"] = "pollution_test"
        
        try:
            with requests.session() as s:
                resp1 = s.get(self.activeLink, params=controlParams1, timeout=5, allow_redirects=False)
                controlText1 = resp1.text
            with requests.session() as s:
                resp2 = s.get(self.activeLink, params=controlParams2, timeout=5, allow_redirects=False)
                controlText2 = resp2.text
        except:
            return
        
        queryResultFrame = CTkFrame(self.autoResultsFrame, fg_color="#2b2b2b", border_width=1, border_color="#444444")
        queryResultFrame.pack(fill="x", padx=10, pady=8)
        
        queryHeaderFrame = CTkFrame(queryResultFrame, fg_color="transparent")
        queryHeaderFrame.pack(fill="x", padx=10, pady=(10, 5))
        
        queryHeaderLabel = CTkLabel(queryHeaderFrame, text="Query Parameter Tests", font=("Arial", 11, "bold"), text_color="#00d9ff")
        queryHeaderLabel.pack(anchor="w")
        
        queryFieldsLabel = CTkLabel(queryHeaderFrame, text=f"Tested Params: {', '.join(originalParams.keys())}", font=("Consolas", 9), text_color="#999999")
        queryFieldsLabel.pack(anchor="w")
        
        querySubFrame = CTkFrame(queryResultFrame, fg_color="transparent")
        querySubFrame.pack(fill="x", padx=10, pady=(0, 10))
        
        vulnFound = False
        controlSimilarity = self.calculateSimilarity(controlText1, controlText2)
        
        sqlVuln = False
        sqlReason = ""
        
        try:
            with requests.session() as s:
                sqlResp = s.get(self.activeLink, params=sqlPayloads, timeout=5, allow_redirects=False)
                sqlText = sqlResp.text
                sqlStatus = sqlResp.status_code
            
            hasSQLError = self.detectSQLErrors(sqlText)
            
            if sqlStatus == 500:
                sqlVuln = True
                sqlReason = f"500 Server Error (Controls stable: {controlSimilarity:.1%})"
            elif hasSQLError:
                sqlVuln = True
                sqlReason = f"Database error detected in response"
            elif controlSimilarity > 0.85:
                diff1 = self.calculateSimilarity(sqlText, controlText1)
                diff2 = self.calculateSimilarity(sqlText, controlText2)
                
                if diff1 < 0.80 and diff2 < 0.80:
                    sqlVuln = True
                    sqlReason = f"Injection response differs significantly (Ctrl similarity: {controlSimilarity:.1%}, Test similarity: {min(diff1, diff2):.1%})"
        except:
            pass
        
        xssVuln = False
        xssReason = ""
        
        try:
            with requests.session() as s:
                xssResp = s.get(self.activeLink, params=xssPayloads, timeout=5, allow_redirects=False)
                xssText = xssResp.text
            
            if "<script>alert(1)</script>" in xssText:
                if "&lt;script&gt;" not in xssText and "&#" not in xssText:
                    xssVuln = True
                    xssReason = f"Unescaped script tag found in response"
        except:
            pass
        
        ppVuln = False
        ppReason = ""
        
        try:
            with requests.session() as s:
                pollutionResp = s.get(self.activeLink, params=pollutionParams, timeout=5, allow_redirects=False)
                pollutionText = pollutionResp.text
                pollutionStatus = pollutionResp.status_code
            
            controlStatus = resp1.status_code
            
            if self.detectParameterPollution(pollutionText, pollutionStatus, controlStatus, "pollution_test"):
                ppVuln = True
                ppReason = "Duplicate parameters accepted and processed by application"
        except:
            pass
        
        tests = [
            ("SQL Injection", sqlVuln, sqlReason),
            ("XSS Injection", xssVuln, xssReason),
            ("Parameter Pollution", ppVuln, ppReason),
        ]
        
        for testName, isVuln, reason in tests:
            color = "#ff4444" if isVuln else "#44ff44"
            status = "VULNERABLE" if isVuln else "SAFE"
            testLabel = CTkLabel(querySubFrame, text=f"{testName}: {status}", font=("Arial", 10, "bold"), text_color=color)
            testLabel.pack(anchor="w", pady=2)
            self.pageTestResults[testName] = {}

            if isVuln:
                vulnFound = True
                self.pageTestResults[testName] = {}
                self.pageTestResults[testName]["result"] = True
                self.pageTestResults[testName]["reason"] = reason
                self.pageTestResults['hasQuery'] =  True
                reasonLabel = CTkLabel(querySubFrame, text=f"  → {reason}", font=("Consolas", 9), text_color="#ffaa44")
                reasonLabel.pack(anchor="w", padx=20)
            else:
                self.pageTestResults[testName]["result"] = False
        
        return vulnFound

    def runFormTests(self):
        for widget in self.autoResultsFrame.winfo_children():
            widget.destroy()
        
        resultsLabel = CTkLabel(self.autoResultsFrame, text="Auto-Test Results", font=("Arial", 12, "bold"))
        resultsLabel.pack(anchor="w", padx=10, pady=(10, 5))
        
        if not self.formData:
            noFormsLabel = CTkLabel(self.autoResultsFrame, text="No forms detected on this page", text_color="gray")
            noFormsLabel.pack(anchor="w", padx=10, pady=5)
            return
        
        resultsLabel = CTkLabel(self.autoResultsFrame, text="Form Parameter Tests", font=("Arial", 11, "bold"), text_color="#aaff44")
        resultsLabel.pack(anchor="w", padx=10, pady=(20, 5))
        
        vulnFound = False
        
        for form_idx, form in enumerate(self.formData):
            testURL = requests.compat.urljoin(self.activeLink, form['action'])
            sqlPayloadDict = {}
            xssPayloadDict = {}
            openRedirectDict = {}
            pathTraversalDict = {}
            ldapPayloadDict = {}
            controlDict1 = {}
            controlDict2 = {}
            testableFields = []
            
            for inputField in form['inputs']:
                inputName = inputField.get('name', inputField.get('id', ''))
                if not inputName or inputField.get('type') == 'submit':
                    continue
                
                testableFields.append(inputName)
                sqlPayloadDict[inputName] = "' OR 1=1 "
                xssPayloadDict[inputName] = "<script>alert(1)</script>"
                openRedirectDict[inputName] = "http://google.com"
                pathTraversalDict[inputName] = "../../../../etc/passwd"
                ldapPayloadDict[inputName] = "*)(uid=*))(|(uid=*"
                controlDict1[inputName] = "Control_Test_1"
                controlDict2[inputName] = "Control_Test_2"
            
            if not sqlPayloadDict:
                continue

            method = form.get('method', 'POST').upper()
            formId = form.get('name') or form.get('id') or f"Form {form_idx + 1}"

            formResultFrame = CTkFrame(self.autoResultsFrame, fg_color="#2b2b2b", border_width=1, border_color="#444444")
            formResultFrame.pack(fill="x", padx=10, pady=8)

            headerFrame = CTkFrame(formResultFrame, fg_color="transparent")
            headerFrame.pack(fill="x", padx=10, pady=(10, 5))
            
            formNameLabel = CTkLabel(headerFrame, text=f"Form: {formId}", font=("Arial", 11, "bold"), text_color="#00d9ff")
            formNameLabel.pack(anchor="w")
            
            methodLabel = CTkLabel(headerFrame, text=f"Method: {method}  |  Submission URL: {testURL}", font=("Consolas", 9), text_color="#999999")
            methodLabel.pack(anchor="w", pady=(2, 0))
            
            fieldsLabel = CTkLabel(headerFrame, text=f"Tested Fields: {', '.join(testableFields)}", font=("Consolas", 9), text_color="#999999")
            fieldsLabel.pack(anchor="w")
            
            sqlVulnerable = False
            xssVulnerable = False
            openRedirectVulnerable = False
            pathTraversalVulnerable = False
            ldapVulnerable = False
            sqlDetectionReason = ""
            xssDetectionReason = ""
            openRedirectReason = ""
            pathTraversalReason = ""
            ldapDetectionReason = ""
            
            try:
                if method == "POST":
                    with requests.session() as s:
                        resp1 = s.post(testURL, data=controlDict1, timeout=5, allow_redirects=False)
                        controlRes1 = resp1.text
                    with requests.session() as s:
                        resp2 = s.post(testURL, data=controlDict2, timeout=5, allow_redirects=False)
                        controlRes2 = resp2.text
                else:
                    with requests.session() as s:
                        resp1 = s.get(testURL, params=controlDict1, timeout=5, allow_redirects=False)
                        controlRes1 = resp1.text
                    with requests.session() as s:
                        resp2 = s.get(testURL, params=controlDict2, timeout=5, allow_redirects=False)
                        controlRes2 = resp2.text

                controlSimilarity = self.calculateSimilarity(controlRes1, controlRes2)

                try:
                    if method == "POST":
                        with requests.session() as s:
                            sqlResponse = s.post(testURL, data=sqlPayloadDict, timeout=5, allow_redirects=False)
                    else:
                        with requests.session() as s:
                            sqlResponse = s.get(testURL, params=sqlPayloadDict, timeout=5, allow_redirects=False)
                    
                    sqlStatus = sqlResponse.status_code
                    sqlTestRes = sqlResponse.text

                    hasSQLError = self.detectSQLErrors(sqlTestRes)
                    
                    if sqlStatus == 500:
                        sqlVulnerable = True
                        sqlDetectionReason = f"500 Server Error (Controls stable: {controlSimilarity:.1%})"
                    elif hasSQLError:
                        sqlVulnerable = True
                        sqlDetectionReason = f"Database error detected in response"
                    elif controlSimilarity > 0.85:
                        diff1 = self.calculateSimilarity(sqlTestRes, controlRes1)
                        diff2 = self.calculateSimilarity(sqlTestRes, controlRes2)
                        
                        if diff1 < 0.80 and diff2 < 0.80:
                            sqlVulnerable = True
                            sqlDetectionReason = f"Injection response differs significantly (Ctrl similarity: {controlSimilarity:.1%}, Test similarity: {min(diff1, diff2):.1%})"
                except Exception as e:
                    pass

                try:
                    if method == "POST":
                        with requests.session() as s:
                            xssResponse = s.post(testURL, data=xssPayloadDict, timeout=5, allow_redirects=False)
                    else:
                        with requests.session() as s:
                            xssResponse = s.get(testURL, params=xssPayloadDict, timeout=5, allow_redirects=False)
                    
                    xssTestRes = xssResponse.text

                    if "<script>alert(1)</script>" in xssTestRes:
                        if "&lt;script&gt;" not in xssTestRes and "&#" not in xssTestRes:
                            xssVulnerable = True
                            xssDetectionReason = f"Unescaped script tag found in response"
                except Exception as e:
                    pass

                try:
                    if method == "POST":
                        with requests.session() as s:
                            orResponse = s.post(testURL, data=openRedirectDict, timeout=5, allow_redirects=False)
                    else:
                        with requests.session() as s:
                            orResponse = s.get(testURL, params=openRedirectDict, timeout=5, allow_redirects=False)
                    
                    isRedirect, redirectTo = self.detectOpenRedirect(orResponse, "google.com", testURL)
                    if isRedirect and redirectTo and "google.com" in redirectTo:
                        openRedirectVulnerable = True
                        openRedirectReason = f"Redirects to external domain: {redirectTo[:50]}"
                except Exception as e:
                    pass

                try:
                    if method == "POST":
                        with requests.session() as s:
                            ptResponse = s.post(testURL, data=pathTraversalDict, timeout=5, allow_redirects=False)
                    else:
                        with requests.session() as s:
                            ptResponse = s.get(testURL, params=pathTraversalDict, timeout=5, allow_redirects=False)
                    
                    if self.detectPathTraversal(ptResponse.text):
                        pathTraversalVulnerable = True
                        pathTraversalReason = f"Sensitive files exposed through path traversal"
                except Exception as e:
                    pass

                try:
                    if method == "POST":
                        with requests.session() as s:
                            ldapResponse = s.post(testURL, data=ldapPayloadDict, timeout=5, allow_redirects=False)
                    else:
                        with requests.session() as s:
                            ldapResponse = s.get(testURL, params=ldapPayloadDict, timeout=5, allow_redirects=False)
                    
                    if "root" in ldapResponse.text.lower() or self.detectLDAPInjection(ldapResponse.text):
                        ldapVulnerable = True
                        ldapDetectionReason = f"LDAP injection detected via filter bypass"
                except Exception as e:
                    pass

            
            except Exception as e:
                errorLabel = CTkLabel(formResultFrame, text=f"Error testing form: {str(e)}", text_color="orange")
                errorLabel.pack(anchor="w", padx=10, pady=5)
                continue

            resultsSubFrame = CTkFrame(formResultFrame, fg_color="transparent")
            resultsSubFrame.pack(fill="x", padx=10, pady=(0, 10))

            tests = [
                ("SQL Injection", sqlVulnerable, sqlDetectionReason),
                ("XSS Injection", xssVulnerable, xssDetectionReason),
                ("Open Redirect", openRedirectVulnerable, openRedirectReason),
                ("Path Traversal", pathTraversalVulnerable, pathTraversalReason),
                ("LDAP Injection", ldapVulnerable, ldapDetectionReason),
            ]

            for testName, isVuln, reason in tests:
                color = "#ff4444" if isVuln else "#44ff44"
                status = "VULNERABLE" if isVuln else "SAFE"
                testLabel = CTkLabel(resultsSubFrame, text=f"{testName}: {status}", font=("Arial", 10, "bold"), text_color=color)
                testLabel.pack(anchor="w", pady=2)
                self.pageTestResults[testName] = {}
                
                if isVuln:
                    vulnFound = True
                    self.pageTestResults[testName]["result"] = True
                    self.pageTestResults[testName]["reason"] = reason
                    self.pageTestResults['hasForm'] =  True
                    reasonLabel = CTkLabel(resultsSubFrame, text=f"  → {reason}", font=("Consolas", 9), text_color="#ffaa44")
                    reasonLabel.pack(anchor="w", padx=20)
                else:
                    self.pageTestResults[testName]["result"] = False

        
        if not vulnFound:
            noVulnLabel = CTkLabel(self.autoResultsFrame, text="✓ No vulnerabilities detected", text_color="#44ff44", font=("Arial", 11, "bold"))
            noVulnLabel.pack(anchor="w", padx=10, pady=10)

    def addToReport(self, app):
        reportEntry = CTkToplevel(self)
        reportEntry.grab_set()
        reportEntry.title("Add Finding to Report")
        reportEntry.geometry("400x300")
        CTkLabel(reportEntry, text="Vulnerability Name", font=("Arial", 14, "bold")).pack(pady=5, padx=10, anchor="w")
        vulnNameEntry = CTkEntry(reportEntry)
        vulnNameEntry.pack(pady=5, padx=10, fill="x")
        CTkLabel(reportEntry, text="Description", font=("Arial", 14, "bold")).pack(pady=5, padx=10, anchor="w")
        vulnDescEntry = CTkTextbox(reportEntry, height=100)
        vulnDescEntry.pack(pady=5, padx=10, fill="both", expand=True)
        submitButton = CTkButton(reportEntry, text="Save Finding", command=lambda: saveFinding())
        submitButton.pack(pady=5, padx=10)
        def saveFinding():
            vulnName = vulnNameEntry.get().strip()
            vulnDesc = vulnDescEntry.get("1.0", END).strip()
            if vulnName and vulnDesc:
                if not app.testResults.get(self.activeLink):
                    app.testResults[self.activeLink] = {}
                app.testResults[self.activeLink][vulnName] = {
                    "result": True,
                    "reason": vulnDesc
                }
                reportEntry.destroy()
            else:
                messagebox.showerror("Error", "Please provide both a vulnerability name and description.")

    def swapView(self, app):
        if self.autoResultsFrame.winfo_ismapped():
            if self.autoTested:
                self.autoTestButton.configure(text="Test Results")
            else:
                self.autoTestButton.configure(text="Auto-Test with Payloads")
            self.autoResultsFrame.grid_remove()
        if self.pageFrame.winfo_ismapped():
            self.pageFrame.grid_remove()
            self.pageButton.configure(text="View Page")
            self.responseFrame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        else:
            self.responseFrame.grid_remove()
            self.pageButton.configure(text="View Response")
            self.pageFrame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        app.update()

    def populateFromForm(self, form):
        self.methodVar.set(form['method'])
        self.urlEntry.delete("1.0", END)
        self.urlEntry.insert("1.0", form['action'])
        
        bodyParts = []
        for inputField in form['inputs']:
            if inputField['name']:
                bodyParts.append(f"{inputField['name']}={inputField['value']}")
        
        if bodyParts and form['method'] == 'POST':
            self.bodyEntry.delete("1.0", END)
            self.bodyEntry.insert("1.0", "&".join(bodyParts))

    def populateFromQueryParams(self):
        paramParts = []
        for key, values in self.queryParams.items():
            for value in values:
                paramParts.append(f"{key}={value}")
        
        if paramParts:
            self.paramsEntry.delete("1.0", END)
            self.paramsEntry.insert("1.0", "&".join(paramParts))

    def parseHeaders(self):
        headersText = self.headersEntry.get("1.0", END).strip()
        headers = {}
        for line in headersText.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()
        return headers

    def sendRequest(self):
        try:
            method = self.methodVar.get()
            url = self.urlEntry.get("1.0", END).strip()
            urlParams = self.paramsEntry.get("1.0", END).strip()
            if urlParams:
                url = urlparse(url)._replace(query=urlParams).geturl()
            headers = self.parseHeaders()
            body = self.bodyEntry.get("1.0", END).strip()
            
            kwargs = {'headers': headers, 'timeout': 10}
            
            match method:
                case 'GET':
                    response = requests.get(url, **kwargs)
                case 'POST':
                    kwargs['data'] = body if body else None
                    response = requests.post(url, **kwargs)
                case 'PUT':
                    kwargs['data'] = body if body else None
                    response = requests.put(url, **kwargs)
                case 'DELETE':
                    response = requests.delete(url, **kwargs)
                case 'PATCH':
                    kwargs['data'] = body if body else None
                    response = requests.patch(url, **kwargs)
                case 'HEAD':
                    response = requests.head(url, **kwargs)
                case _:
                    response = requests.get(url, **kwargs)
      
            self.lastResponse = response
            self.lastResponseHeaders = dict(response.headers)

            statusText = f"Status: {response.status_code} - {response.reason}"
            self.statusLabel.configure(text=statusText)

            self.responseHeadersText.configure(state="normal")
            self.responseHeadersText.delete("1.0", END)
            for key, value in response.headers.items():
                self.responseHeadersText.insert(END, f"{key}: {value}\n")
            self.responseHeadersText.configure(state="disabled")
            
            try:
                bodyContent = json.dumps(response.json(), indent=2)
            except:
                try:
                    soup = BeautifulSoup(response.text, "html.parser")
                    bodyContent = soup.prettify()
                except:
                    bodyContent = response.text
            
            self.responseBodyText.configure(state="normal")
            self.responseBodyText.delete("1.0", END)
            self.responseBodyText.insert("1.0", bodyContent)
            self.responseBodyText.configure(state="disabled")
            try:
                self.pageFrame.load_html(bodyContent)
            except Exception as e:
                self.pageFrame.load_html(f"<h1>Error loading page:</h1><p>{e}</p>")
            
        except requests.exceptions.Timeout:
            self.statusLabel.configure(text="Status: Timeout", text_color="red")
            self.showResponseError("Request timed out")
        except requests.exceptions.ConnectionError:
            self.statusLabel.configure(text="Status: Connection Error", text_color="red")
            self.showResponseError("Connection error")
        except Exception as e:
            self.statusLabel.configure(text="Status: Error", text_color="red")
            self.showResponseError(f"Error: {str(e)}")
        
    def showResponseError(self, errorText):
        self.responseBodyText.configure(state="normal")
        self.responseBodyText.delete("1.0", END)
        self.responseBodyText.insert("1.0", errorText)
        self.responseBodyText.configure(state="disabled")

def renderLink(app, activeLink):
    print(f"Rendering page for: {activeLink}")
    requestData = []
    responseData = []
    loadingFrame = CTkFrame(app.base)
    loadingFrame.grid(row=0, column=0, sticky="nsew")
    loadingLabel = CTkLabel(loadingFrame, text="Rendering page...")
    loadingLabel.pack(pady=20)
    app.update()
    with sync_playwright() as playwright:
        chromium = playwright.chromium
        browser = chromium.launch()
        page = browser.new_page()
        
        page.on("request", lambda request: requestData.append(request))
        page.on("response", lambda response: responseData.append(response))
        page.goto(activeLink)      
        pageToRender = page.content()
        
        browser.close()
        
        app.makeFrame(RenderPage, pageToRender, activeLink, loadingLabel, requestData, responseData)
    app.showFrame("RenderPage")
    loadingFrame.destroy()

class RenderPage(CTkFrame):
    def __init__(self, parent, app, pageToRender, activeLink, loadingLabel, requestData=None, responseData=None):
        CTkFrame.__init__(self, parent)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_propagate(False)

        self.renderBool = True

        header = CTkLabel(self, text=f"Rendered View - {activeLink}", font=("Arial", 16, "bold"))
        header.grid(row=0, column=0, pady=10, padx=10, columnspan=2, sticky="w")
        
        buttonFrame = CTkFrame(self, fg_color="transparent")
        buttonFrame.grid(row=0, column=1, sticky="e", padx=10, pady=10)

        returnButton = CTkButton(buttonFrame, text="Return to Crawl Tree", command=lambda: app.showFrame("CrawlListPage"))
        returnButton.pack(side="left", padx=5)
        
        openInBrowserButton = CTkButton(buttonFrame, text="Open in Browser", command=lambda: webbrowser.open(activeLink))
        openInBrowserButton.pack(side="left", padx=5)

        self.swapButton = CTkButton(buttonFrame, text="View Raw HTML", command=lambda: self.swapRenFrame())
        self.swapButton.pack(side="left", padx=5)
        
        extractLinksButton = CTkButton(buttonFrame, text="Extract Links", command=lambda: self.extractLinksFromPage(pageToRender, activeLink, app))
        extractLinksButton.pack(side="left", padx=5)

        loadingLabel.configure(text="Prettifying HTML...")
        app.update()
        self.rawTextFrame = CTkScrollableFrame(self)
        self.rawTextFrame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        CTkLabel(self.rawTextFrame, text="Raw HTML Content", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        htmlContentLabel = CTkLabel(self.rawTextFrame, text=BeautifulSoup(pageToRender, "html.parser").find('body').prettify(), font=("Consolas", 9), wraplength=580, justify="left")
        htmlContentLabel.pack(anchor="w", padx=10, pady=2)

        loadingLabel.configure(text="Opening Page...")
        app.update()
        self.renderFrame = HtmlFrame(self, horizontal_scrollbar="auto", messages_enabled=False)
        try:
            self.renderFrame.load_html(pageToRender)
        except Exception as e:
            self.renderFrame.load_html(f"<h1>Error loading page:</h1><p>{e}</p>")
        self.renderFrame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        requestFrame = CTkScrollableFrame(self)
        requestFrame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        CTkLabel(requestFrame, text="Request Information", font=("Arial", 12, "bold")).pack(anchor="c", padx=10, pady=(10, 5))
        CTkLabel(requestFrame, text=f"URL: {activeLink}", font=("Consolas", 9), wraplength=300, justify="left").pack(anchor="w", padx=10, pady=2)
        CTkLabel(requestFrame, text=f"Method: {requestData[0].method}", font=("Consolas", 9)).pack(anchor="w", padx=10, pady=2)
        CTkLabel(requestFrame, text="Headers:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        for header_key, header_value in requestData[0].headers.items():
            header_text = f"{header_key}: {header_value}"
            CTkLabel(requestFrame, text=header_text, font=("Consolas", 8), wraplength=300, justify="left", text_color="gray80").pack(anchor="w", padx=20, pady=1)
        if requestData[0].post_data:
            CTkLabel(requestFrame, text="Post Data:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
            postDataText = requestData[0].post_data
            CTkLabel(requestFrame, text=postDataText, font=("Consolas", 8), wraplength=300, justify="left", text_color="gray80").pack(anchor="w", padx=20, pady=1)
        CTkLabel(requestFrame, text="Response Information", font=("Arial", 12, "bold")).pack(anchor="c", padx=10, pady=(10, 5))
        CTkLabel(requestFrame, text=f"Status Code: {responseData[0].status} - {responseData[0].status_text if responseData[0].status_text else 'N/A'}", font=("Consolas", 9)).pack(anchor="w", padx=10, pady=2)
        CTkLabel(requestFrame, text="Headers:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        for header_key, header_value in responseData[0].headers.items():
            header_text = f"{header_key}: {header_value}"
            CTkLabel(requestFrame, text=header_text, font=("Consolas", 8), wraplength=300, justify="left", text_color="gray80").pack(anchor="w", padx=20, pady=1)
        CTkLabel(requestFrame, text=f"Content Length: {len(pageToRender)} characters", font=("Consolas", 9)).pack(anchor="w", padx=10, pady=2)    
        
    def swapRenFrame(self):
        self.renderBool = not self.renderBool
        print(f"Swapping renderBool to: {self.renderBool}")
        if self.renderBool:
            self.swapButton.configure(text="View Raw HTML")
            self.renderFrame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
            self.rawTextFrame.grid_forget()
        else:
            self.swapButton.configure(text="View Render")
            self.rawTextFrame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
            self.renderFrame.grid_forget()
    
    def extractLinksFromPage(self, pageToRender, activeLink, app):
        try:
            soup = BeautifulSoup(pageToRender, "html.parser")
            links = soup.select("a[href]")
            
            extracted_count = 0
            for link in links:
                url = link.get('href', '')
                if not url.startswith("#") and not url.startswith("mailto") and url.strip():
                    if not url.startswith("http"):
                        url = requests.compat.urljoin(activeLink, url)
                        if url not in app.visitedUrls:
                            app.visitedUrls.append(url)
                            crawlPage = app.frames["CrawlListPage"]
                            crawlPage.addTree(url, app)
                            extracted_count += 1
            
            print(f"Extracted {extracted_count} new links from {activeLink}")
            messagebox.showinfo("Links Extracted", f"Successfully extracted {extracted_count} new links from this page.")
            
            app.frames["CrawlListPage"].refreshTree(app)
            
        except Exception as e:
            print(f"Error extracting links: {e}")
            messagebox.showerror("Error", f"Error extracting links: {e}")
    
    def __del__(self):
        try:
            os.remove(self.tempFile.name)
        except Exception as E:
            print(f"Error deleting temp file: {E}")

if __name__ == "__main__":
    set_appearance_mode("dark")
    set_default_color_theme("dark-blue")
    root = App()
    root.mainloop()