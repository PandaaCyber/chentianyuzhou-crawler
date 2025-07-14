import requests
import time
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import html2text
from ebooklib import epub
import datetime

class ChentianYuZhouCrawler:
    def __init__(self):
        self.base_url = "https://chentianyuzhou.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.articles = []
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = False
        
    def get_article_links(self):
        """获取所有文章链接"""
        print("正在获取文章列表...")
        
        # 尝试获取首页
        try:
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找文章链接 - 这需要根据网站结构调整
            article_links = set()
            
            # 常见的文章链接选择器
            selectors = [
                'a[href*="/posts/"]',
                'a[href*="/post/"]', 
                'a[href*="/articles/"]',
                'a[href*="/blog/"]',
                '.post-title a',
                '.entry-title a',
                'h2 a',
                'h3 a'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        article_links.add(full_url)
            
            # 如果没有找到文章链接，尝试查找所有内部链接
            if not article_links:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link['href']
                    if href.startswith('/') or self.base_url in href:
                        full_url = urljoin(self.base_url, href)
                        # 过滤掉明显不是文章的链接
                        if not any(x in full_url.lower() for x in ['#', 'javascript:', 'mailto:', '.css', '.js', '.jpg', '.png', '.gif']):
                            article_links.add(full_url)
            
            print(f"找到 {len(article_links)} 个可能的文章链接")
            return list(article_links)
            
        except Exception as e:
            print(f"获取文章列表失败: {e}")
            return []
    
    def crawl_article(self, url):
        """爬取单篇文章"""
        try:
            print(f"正在爬取: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 获取标题
            title = None
            title_selectors = ['h1', '.post-title', '.entry-title', 'title']
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text().strip()
                    break
            
            if not title:
                title = f"文章 - {url.split('/')[-1]}"
            
            # 获取内容
            content = None
            content_selectors = [
                '.post-content',
                '.entry-content', 
                '.content',
                'article',
                '.post',
                'main'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem
                    break
            
            if not content:
                # 如果没有找到内容区域，尝试获取body中的主要内容
                content = soup.find('body')
            
            if content:
                # 清理不需要的元素
                for elem in content.select('script, style, nav, footer, header, .comment'):
                    elem.decompose()
                
                # 转换为markdown
                markdown_content = self.h2t.handle(str(content))
                
                # 清理markdown内容
                markdown_content = self.clean_markdown(markdown_content)
                
                article_data = {
                    'title': title,
                    'url': url,
                    'content': markdown_content,
                    'date': datetime.datetime.now().strftime('%Y-%m-%d')
                }
                
                return article_data
            
        except Exception as e:
            print(f"爬取文章失败 {url}: {e}")
            return None
    
    def clean_markdown(self, content):
        """清理markdown内容"""
        # 移除多余的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        # 移除行首行尾空白
        lines = [line.strip() for line in content.split('\n')]
        return '\n'.join(lines)
    
    def save_markdown_files(self):
        """保存markdown文件"""
        if not os.path.exists('articles'):
            os.makedirs('articles')
        
        for i, article in enumerate(self.articles, 1):
            # 清理文件名
            safe_title = re.sub(r'[^\w\s-]', '', article['title'])
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            filename = f"{i:03d}-{safe_title[:50]}.md"
            
            filepath = os.path.join('articles', filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {article['title']}\n\n")
                f.write(f"原文链接: {article['url']}\n")
                f.write(f"爬取日期: {article['date']}\n\n")
                f.write("---\n\n")
                f.write(article['content'])
            
            print(f"已保存: {filename}")
    
    def create_epub(self):
        """创建EPUB电子书"""
        print("正在创建EPUB电子书...")
        
        # 创建epub对象
        book = epub.EpubBook()
        
        # 设置书籍信息
        book.set_identifier('chentianyuzhou-collection')
        book.set_title('陈天宇宙 - 文章集合')
        book.set_language('zh-CN')
        book.add_author('陈天宇宙')
        
        # 添加封面页
        intro_chapter = epub.EpubHtml(
            title='前言',
            file_name='intro.xhtml',
            lang='zh-CN'
        )
        intro_content = f"""
        <h1>陈天宇宙 - 文章集合</h1>
        <p>本电子书包含了陈天宇宙网站的文章集合。</p>
        <p>原网站地址: <a href="https://chentianyuzhou.com">https://chentianyuzhou.com</a></p>
        <p>生成时间: {datetime.datetime.now().strftime('%Y年%m月%d日')}</p>
        <p>共收录文章: {len(self.articles)} 篇</p>
        """
        intro_chapter.content = intro_content
        book.add_item(intro_chapter)
        
        # 创建目录
        toc_items = [intro_chapter]
        spine = ['nav', intro_chapter]
        
        # 添加文章章节
        for i, article in enumerate(self.articles, 1):
            # 创建章节
            chapter = epub.EpubHtml(
                title=article['title'],
                file_name=f'chapter_{i:03d}.xhtml',
                lang='zh-CN'
            )
            
            # 将markdown转换为HTML
            chapter_content = f"""
            <h1>{article['title']}</h1>
            <p><strong>原文链接:</strong> <a href="{article['url']}">{article['url']}</a></p>
            <p><strong>爬取日期:</strong> {article['date']}</p>
            <hr/>
            """
            
            # 简单的markdown到html转换
            md_content = article['content']
            # 这里可以使用更复杂的markdown解析器，但为了简化就做基本转换
            md_content = md_content.replace('\n\n', '</p><p>')
            md_content = f"<p>{md_content}</p>"
            md_content = re.sub(r'# (.*?)</p>', r'<h1>\1</h1>', md_content)
            md_content = re.sub(r'## (.*?)</p>', r'<h2>\1</h2>', md_content)
            md_content = re.sub(r'### (.*?)</p>', r'<h3>\1</h3>', md_content)
            
            chapter_content += md_content
            chapter.content = chapter_content
            
            book.add_item(chapter)
            toc_items.append(chapter)
            spine.append(chapter)
        
        # 设置目录
        book.toc = toc_items
        book.spine = spine
        
        # 添加导航文件
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # 写入epub文件
        epub_filename = f'陈天宇宙-文章集合-{datetime.datetime.now().strftime("%Y%m%d")}.epub'
        epub.write_epub(epub_filename, book)
        
        print(f"EPUB电子书已创建: {epub_filename}")
        return epub_filename
    
    def run(self):
        """运行爬虫"""
        print("开始爬取陈天宇宙网站...")
        
        # 获取文章链接
        article_links = self.get_article_links()
        
        if not article_links:
            print("没有找到文章链接，请检查网站结构")
            return
        
        # 爬取文章
        for url in article_links[:20]:  # 限制爬取数量，避免过度请求
            article = self.crawl_article(url)
            if article:
                self.articles.append(article)
            time.sleep(1)  # 礼貌性延迟
        
        if not self.articles:
            print("没有成功爬取到任何文章")
            return
        
        print(f"成功爬取 {len(self.articles)} 篇文章")
        
        # 保存markdown文件
        self.save_markdown_files()
        
        # 创建epub
        epub_file = self.create_epub()
        
        print(f"任务完成！生成了 {len(self.articles)} 篇文章的markdown文件和epub电子书")

if __name__ == "__main__":
    crawler = ChentianYuZhouCrawler()
    crawler.run()
