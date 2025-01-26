import sys
import os
import asyncio
import requests
from xml.etree import ElementTree
from urllib.parse import urlparse

import chromadb
from chromadb.utils import embedding_functions
import google.generativeai as genai

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QFileDialog, 
    QProgressBar, QMessageBox, QTextEdit, QSplitter,
    QLineEdit, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPalette, QColor, QFont, QTextCursor

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

class ChromaDBManager:
    def __init__(self, collection_name='web_documents'):
        embedding_function = embedding_functions.ONNXMiniLM_L6_V2()
        
        self.client = chromadb.PersistentClient(path="./chroma_storage")
        self.collection = self.client.get_or_create_collection(
            name=collection_name, 
            embedding_function=embedding_function
        )

    def add_documents(self, documents, metadata=None):
        # Generate unique IDs for each document
        ids = [f"doc_{hash(doc)}" for doc in documents]
        
        # Add documents to the collection
        self.collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadata
        )

    def search_documents(self, query, n_results=5):
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results['documents'][0]

class CrawlerThread(QThread):
    update_signal = pyqtSignal(int)  # Progress percentage
    finished_signal = pyqtSignal(bool, list)

    def __init__(self, sitemap_url, output_dir):
        super().__init__()
        self.sitemap_url = sitemap_url
        self.output_dir = output_dir
        self.chroma_manager = ChromaDBManager()

    def get_sitemap_urls(self):            
        try:
            response = requests.get(self.sitemap_url)
            response.raise_for_status()
            
            root = ElementTree.fromstring(response.content)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]
            
            return urls
        except Exception as e:
            return []

    async def crawl_sequential(self, urls):
        os.makedirs(self.output_dir, exist_ok=True)

        browser_config = BrowserConfig(
            headless=True,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )

        crawl_config = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator()
        )

        crawler = AsyncWebCrawler(config=browser_config)
        await crawler.start()

        crawled_documents = []

        try:
            total_urls = len(urls)
            session_id = "session1"
            for index, url in enumerate(urls, 1):
                result = await crawler.arun(
                    url=url,
                    config=crawl_config,
                    session_id=session_id
                )
                if result.success:
                    parsed_url = urlparse(url)
                    filepath = os.path.join(
                        self.output_dir,
                        f"{parsed_url.netloc}{parsed_url.path}".replace('/', '_')
                    )
                    
                    if not filepath.endswith('.md'):
                        filepath += '.md'
                    
                    try:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(result.markdown_v2.raw_markdown)
                        
                        # Add document to crawled_documents for ChromaDB
                        crawled_documents.append(result.markdown_v2.raw_markdown)
                    except Exception:
                        pass
                
                # Update progress
                progress = int((index / total_urls) * 100)
                self.update_signal.emit(progress)
        finally:
            await crawler.close()

        # Add crawled documents to ChromaDB
        if crawled_documents:
            self.chroma_manager.add_documents(crawled_documents)

        return crawled_documents

    def run(self):
        try:
            urls = self.get_sitemap_urls()
            if urls:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                documents = loop.run_until_complete(self.crawl_sequential(urls))
                
                self.finished_signal.emit(True, documents)
            else:
                self.finished_signal.emit(False, [])
        except Exception:
            self.finished_signal.emit(False, [])

class WebCrawlerGeminiApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.chroma_manager = ChromaDBManager()

    def initUI(self):
        # Dark theme palette
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        self.setPalette(palette)

        self.setWindowTitle('Web Crawler & Semantic Search')
        self.setGeometry(100, 100, 1200, 800)

        # Main layout
        main_layout = QHBoxLayout()
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Column 1: Crawler
        crawler_widget = QWidget()
        crawler_layout = QVBoxLayout()

        # Sitemap URL input
        url_layout = QHBoxLayout()
        url_label = QLabel('Sitemap URL:')
        self.url_input = QLineEdit()
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        crawler_layout.addLayout(url_layout)

        # Output directory input
        dir_layout = QHBoxLayout()
        dir_label = QLabel('Output Directory:')
        self.dir_input = QLineEdit()
        dir_button = QPushButton('Browse')
        dir_button.clicked.connect(self.browse_directory)
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(dir_button)
        crawler_layout.addLayout(dir_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        crawler_layout.addWidget(self.progress_bar)

        # Crawl button
        self.crawl_button = QPushButton('Start Crawling')
        self.crawl_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.crawl_button.clicked.connect(self.start_crawling)
        crawler_layout.addWidget(self.crawl_button)

        crawler_widget.setLayout(crawler_layout)
        splitter.addWidget(crawler_widget)

        # Column 2: Gemini Search
        search_widget = QWidget()
        search_layout = QVBoxLayout()

        # Gemini API Key
        api_layout = QHBoxLayout()
        api_label = QLabel('Gemini API Key:')
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_key_input)
        search_layout.addLayout(api_layout)

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        search_layout.addWidget(self.chat_display)

        # Query input
        query_layout = QHBoxLayout()
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText('Enter your query...')
        self.search_button = QPushButton('Search')
        self.search_button.clicked.connect(self.perform_semantic_search)
        query_layout.addWidget(self.query_input)
        query_layout.addWidget(self.search_button)
        search_layout.addLayout(query_layout)

        search_widget.setLayout(search_layout)
        splitter.addWidget(search_widget)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, 'Select Output Directory')
        self.dir_input.setText(dir_path)

    def start_crawling(self):
        # Validate inputs
        sitemap_url = self.url_input.text().strip()
        output_dir = self.dir_input.text().strip()

        if not sitemap_url:
            QMessageBox.warning(self, 'Error', 'Please enter a sitemap URL')
            return

        if not output_dir:
            QMessageBox.warning(self, 'Error', 'Please select an output directory')
            return

        # Disable crawl button and reset progress
        self.crawl_button.setEnabled(False)
        self.progress_bar.setValue(0)

        # Start crawling thread
        self.crawler_thread = CrawlerThread(sitemap_url, output_dir)
        self.crawler_thread.update_signal.connect(self.update_progress)
        self.crawler_thread.finished_signal.connect(self.crawling_finished)
        self.crawler_thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def crawling_finished(self, success, documents):
        self.crawl_button.setEnabled(True)
        if success:
            QMessageBox.information(self, 'Success', 'Crawling completed successfully!')
        else:
            QMessageBox.warning(self, 'Error', 'Crawling encountered an issue')

    def perform_semantic_search(self):
        api_key = self.api_key_input.text().strip()
        query = self.query_input.text().strip()

        if not api_key:
            QMessageBox.warning(self, 'Error', 'Please enter a Gemini API Key')
            return

        if not query:
            QMessageBox.warning(self, 'Error', 'Please enter a query')
            return

        try:
            # Configure Gemini
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

            # Retrieve relevant documents from ChromaDB
            context_docs = self.chroma_manager.search_documents(query)
            context = "\n\n".join(context_docs)

            # Construct prompt with context
            full_prompt = f"Context:\n{context}\n\nQuery: {query}\n\nProvide a precise answer based only on the context above."

            # Generate response
            response = model.generate_content(full_prompt)

            # Update chat display
            self.update_chat(f"You: {query}\n\nAI: {response.text}")

            # Clear query input
            self.query_input.clear()

        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Search failed: {str(e)}')

    def update_chat(self, message):
        self.chat_display.append(message)
        self.chat_display.append("\n" + "-"*50 + "\n")
        # Scroll to bottom
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)

def main():
    app = QApplication(sys.argv)
    ex = WebCrawlerGeminiApp()
    ex.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()