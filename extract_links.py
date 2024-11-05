"""
CCTV 圖片連結提取器
功能：
1. 提取網頁中的 CCTV 圖片連結
2. 管理和編輯連結
3. 自動分頁（每頁9個連結）
4. 提供本地伺服器顯示監控畫面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
from bs4 import BeautifulSoup
from threading import Thread
import webbrowser
import json
from datetime import datetime
import os
import threading
import http.server
import socketserver
import time

# 全域變數
PORT = 8000  # 伺服器埠號
server_thread = None  # 伺服器執行緒

def start_server():
    """啟動 HTTP 伺服器"""
    Handler = http.server.SimpleHTTPRequestHandler
    
    # 嘗試多個端口
    for port in range(8000, 8010):
        try:
            with socketserver.TCPServer(("", port), Handler) as httpd:
                global PORT
                PORT = port
                print(f"伺服器執行於 http://localhost:{PORT}")
                httpd.serve_forever()
                break
        except OSError:
            continue

class LinkExtractorGUI:     
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV 圖片連結提取器")
        self.root.geometry("800x600")
        
        # 啟動伺服器
        global server_thread
        if server_thread is None:
            server_thread = threading.Thread(target=start_server, daemon=True)
            server_thread.start()
            # 等待伺服器啟動
            time.sleep(1)
            
            # 確認伺服器是否啟動成功
            max_retries = 5
            for _ in range(max_retries):
                try:
                    requests.get(f'http://localhost:{PORT}', timeout=1)
                    print("伺服器啟動成功")
                    # 自動開啟監視器頁面
                    webbrowser.open(f'http://localhost:{PORT}/display_grid.html')
                    break
                except:
                    time.sleep(1)
            else:
                print("伺服器啟動失敗")
        
        # 創建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # URL 輸入區域
        self.url_frame = ttk.Frame(self.main_frame)
        self.url_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.url_label = ttk.Label(self.url_frame, text="網址:")
        self.url_label.pack(side=tk.LEFT)
        
        self.url_entry = ttk.Entry(self.url_frame)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        
        self.extract_button = ttk.Button(
            self.url_frame, 
            text="提取結",
            command=self.start_extraction
        )
        self.extract_button.pack(side=tk.LEFT)
        
        # 進度條
        self.progress = ttk.Progressbar(
            self.main_frame,
            mode='indeterminate'
        )
        
        # 結顯示區域
        self.result_frame = ttk.LabelFrame(self.main_frame, text="提取結果", padding="5")
        self.result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = scrolledtext.ScrolledText(
            self.result_frame,
            wrap=tk.WORD,
            width=40,
            height=10
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # 為文字區域添加點擊事件
        self.result_text.tag_configure("hyperlink", foreground="blue", underline=1)
        self.result_text.tag_bind("hyperlink", "<Button-1>", self.open_link)
        self.result_text.tag_bind("hyperlink", "<Enter>", lambda e: self.result_text.configure(cursor="hand2"))
        self.result_text.tag_bind("hyperlink", "<Leave>", lambda e: self.result_text.configure(cursor=""))
        
        # 為輸入框加入右鍵選單
        self.create_right_click_menu()
        
        # 狀態列
        self.status_label = ttk.Label(
            self.main_frame,
            text="就緒",
            anchor=tk.W
        )
        self.status_label.pack(fill=tk.X, pady=(5, 0))
        
        # 添加存按鈕
        self.save_button = ttk.Button(
            self.url_frame, 
            text="儲存結果",
            command=self.save_results,
            state=tk.DISABLED
        )
        self.save_button.pack(side=tk.LEFT, padx=(5, 0))
        
        self.current_links = []  # 儲存當前的連結
        
        # 添加編輯 JSON 按鈕
        self.edit_json_button = ttk.Button(
            self.url_frame, 
            text="編輯JSON",
            command=self.open_json_editor
        )
        self.edit_json_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # 添加開啟 HTML 按鈕
        self.open_html_button = ttk.Button(
            self.url_frame, 
            text="開啟監視器",
            command=self.open_html_viewer
        )
        self.open_html_button.pack(side=tk.LEFT, padx=(5, 0))
    
    def create_right_click_menu(self):
        # 創建右鍵選單
        self.right_click_menu = tk.Menu(self.root, tearoff=0)
        self.right_click_menu.add_command(label="剪下", command=lambda: self.right_click_menu_action('cut'))
        self.right_click_menu.add_command(label="複製", command=lambda: self.right_click_menu_action('copy'))
        self.right_click_menu.add_command(label="貼上", command=lambda: self.right_click_menu_action('paste'))
        
        # 綁定右鍵事件到所有可編輯元件
        self.url_entry.bind('<Button-3>', self.show_right_click_menu)
        self.result_text.bind('<Button-3>', self.show_right_click_menu)
        
        # 為編輯器中的輸入框也添加右鍵選單
        def bind_right_click_to_entries(entries):
            for entry in entries:
                entry.bind('<Button-3>', self.show_right_click_menu)
    
    def show_right_click_menu(self, event):
        try:
            self.right_click_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.right_click_menu.grab_release()
    
    def right_click_menu_action(self, action):
        try:
            focused = self.root.focus_get()
            if action == 'cut':
                focused.event_generate('<<Cut>>')
            elif action == 'copy':
                focused.event_generate('<<Copy>>')
            elif action == 'paste':
                focused.event_generate('<<Paste>>')
        except:
            pass
    
    def extract_links(self, url):
        try:
            # 發送 GET 請求
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 直接找到所有 class="cctv-image" 的 img 標籤
            images = soup.find_all('img', class_='cctv-image')
            
            # 提取 src 屬性
            links = []
            for img in images:
                if 'src' in img.attrs:
                    links.append(img['src'])
            
            return links
            
        except Exception as e:
            return f"錯誤: {str(e)}"
    
    def start_extraction(self):
        # 清空結果
        self.result_text.delete(1.0, tk.END)
        url = self.url_entry.get().strip()
        
        if not url:
            self.status_label.config(text="請輸入網址")
            return
        
        # 顯示進度條
        self.progress.pack(fill=tk.X, pady=(0, 10))
        self.progress.start()
        self.extract_button.config(state=tk.DISABLED)
        self.status_label.config(text="正在提取連結...")
        
        # 在新線程中執行提取
        Thread(target=self.extraction_thread, args=(url,), daemon=True).start()
    
    def extraction_thread(self, url):
        # 執行提取
        links = self.extract_links(url)
        
        # 更新 GUI（在主線程中）
        self.root.after(0, self.update_results, links)
    
    def update_results(self, links):
        # 停止進度條
        self.progress.stop()
        self.progress.pack_forget()
        self.extract_button.config(state=tk.NORMAL)
        
        # 顯示結果
        if isinstance(links, str):  # 如果是錯誤訊息
            self.result_text.insert(tk.END, links)
            self.status_label.config(text="提取失敗")
            self.save_button.config(state=tk.DISABLED)
        else:
            if links:
                self.current_links = links  # 儲存連結
                for link in links:
                    self.result_text.insert(tk.END, link + "\n", "hyperlink")
                self.status_label.config(text=f"成功提取 {len(links)} 個圖片連結")
                self.save_button.config(state=tk.NORMAL)  # 啟用儲存按鈕
            else:
                self.result_text.insert(tk.END, "沒有找到圖片連結")
                self.status_label.config(text="未找到圖片連結")
                self.save_button.config(state=tk.DISABLED)
    
    def save_results(self):
        if not self.current_links:
            return
            
        filename = "cctv_links.json"
        current_data = {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "pages": []
        }
        
        try:
            # 讀取現有的 JSON 檔案
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if "pages" in existing_data:
                        current_data["pages"] = existing_data["pages"]
            except (FileNotFoundError, json.JSONDecodeError):
                current_data["pages"] = [[]]  # 如果檔案不存在，創建第一頁
            
            # 取得所有現有連結
            existing_links = set()
            for page in current_data["pages"]:
                existing_links.update(page)
            
            # 添加新的連結
            for link in self.current_links:
                if link not in existing_links:  # 如果是新連結
                    # 找到最後一頁
                    if not current_data["pages"]:
                        current_data["pages"].append([])
                    last_page = current_data["pages"][-1]
                    
                    # 如果最後一頁已滿，創建新頁面
                    if len(last_page) >= 9:
                        last_page = []
                        current_data["pages"].append(last_page)
                    
                    # 添加連結到最後一頁
                    last_page.append(link)
                    existing_links.add(link)
            
            # 儲存更新後的資料
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            
            total_pages = len(current_data["pages"])
            total_links = sum(len(page) for page in current_data["pages"])
            self.status_label.config(text=f"已更新 {filename}，共 {total_links} 個連結，{total_pages} 頁")
            
            # 清空當前連結列表
            self.current_links = []
            self.save_button.config(state=tk.DISABLED)
            
        except Exception as e:
            self.status_label.config(text=f"儲存失敗: {str(e)}")
    
    def open_link(self, event):
        # 獲取點擊位置的行
        index = self.result_text.index(f"@{event.x},{event.y}")
        line_start = self.result_text.index(f"{index} linestart")
        line_end = self.result_text.index(f"{index} lineend")
        
        # 獲取該行的連結
        link = self.result_text.get(line_start, line_end).strip()
        
        # 如果連結不是以 http 開頭，加上 https://
        if not link.startswith(('http://', 'https://')):
            link = 'https://' + link
            
        # 開啟連結
        try:
            webbrowser.open(link)
        except Exception as e:
            self.status_label.config(text=f"無法開啟連結: {str(e)}")
    
    def open_json_editor(self):
        editor_window = tk.Toplevel(self.root)
        editor_window.title("編輯 JSON")
        editor_window.geometry("800x600")
        
        # 創建主框架
        main_frame = ttk.Frame(editor_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 分頁控制框架
        page_control_frame = ttk.Frame(main_frame)
        page_control_frame.pack(fill=tk.X, pady=(0, 10))
        
        current_page = [0]  # 使用列表來儲存當前頁碼，以便在函數內部修改
        
        def update_page_label():
            page_label.config(text=f"第 {current_page[0] + 1} 頁")
        
        # 上一頁按鈕
        prev_button = ttk.Button(
            page_control_frame,
            text="上一頁",
            command=lambda: change_page(-1)
        )
        prev_button.pack(side=tk.LEFT)
        
        # 頁碼標籤
        page_label = ttk.Label(page_control_frame, text="第 1 頁")
        page_label.pack(side=tk.LEFT, padx=10)
        
        # 下一頁按鈕
        next_button = ttk.Button(
            page_control_frame,
            text="下一頁",
            command=lambda: change_page(1)
        )
        next_button.pack(side=tk.LEFT)
        
        # 連結列表框架
        links_frame = ttk.LabelFrame(main_frame, text="連結列表", padding="5")
        links_frame.pack(fill=tk.BOTH, expand=True)
        
        # 儲存所有頁面的輸入框
        all_entries = []
        
        def create_page():
            page_frame = ttk.Frame(links_frame)
            page_entries = []
            
            for i in range(9):  # 每頁9個輸入框
                row_frame = ttk.Frame(page_frame)
                row_frame.pack(fill=tk.X, pady=2)
                
                # 連結輸入框
                entry = ttk.Entry(row_frame)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                # 綁定右鍵選單
                entry.bind('<Button-3>', self.show_right_click_menu)
                page_entries.append(entry)
                
                # 測試按鈕
                test_button = ttk.Button(
                    row_frame,
                    text="測試",
                    command=lambda e=entry: test_link(e.get())
                )
                test_button.pack(side=tk.LEFT, padx=(5, 0))
                
                # 刪除按鈕
                delete_button = ttk.Button(
                    row_frame,
                    text="刪除",
                    command=lambda e=entry: e.delete(0, tk.END)
                )
                delete_button.pack(side=tk.LEFT, padx=(5, 0))
            
            return page_frame, page_entries
        
        def change_page(delta):
            # 隱藏當前頁面
            if all_entries:
                all_entries[current_page[0]][0].pack_forget()
            
            # 計算新頁碼
            current_page[0] = (current_page[0] + delta) % len(all_entries)
            if current_page[0] < 0:
                current_page[0] = len(all_entries) - 1
            
            # 顯示新頁面
            if all_entries:
                all_entries[current_page[0]][0].pack(fill=tk.BOTH, expand=True)
            update_page_label()
        
        def load_links():
            try:
                with open("cctv_links.json", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("pages", [])
            except:
                return [[]]
        
        # 載入現有連結並創建頁面
        pages = load_links()
        for page in pages:
            page_frame, page_entries = create_page()
            for entry, link in zip(page_entries, page + [''] * (9 - len(page))):
                entry.insert(0, link)
            all_entries.append((page_frame, page_entries))
        
        # 如果沒有頁面，創建一個空頁面
        if not all_entries:
            page_frame, page_entries = create_page()
            all_entries.append((page_frame, page_entries))
        
        # 顯示第一頁
        all_entries[0][0].pack(fill=tk.BOTH, expand=True)
        
        def test_link(url):
            if url.strip():
                webbrowser.open(url)
        
        def save_changes():
            try:
                # 收集所有頁面的連結
                all_links = []
                for _, page_entries in all_entries:
                    page_links = []
                    for entry in page_entries:
                        link = entry.get().strip()
                        if link:  # 如果連結不是空的
                            page_links.append(link)
                    if page_links:  # 如果這一頁有連結
                        all_links.append(page_links)
                
                # 儲存到 JSON
                data = {
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                    "pages": all_links
                }
                
                with open("cctv_links.json", 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("成功", f"已儲存 {sum(len(page) for page in all_links)} 個連結，共 {len(all_links)} 頁")
                editor_window.destroy()
                
            except Exception as e:
                messagebox.showerror("錯誤", str(e))
        
        # 按鈕框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 新增頁面按鈕
        add_page_button = ttk.Button(
            button_frame,
            text="新增頁面",
            command=lambda: add_new_page()
        )
        add_page_button.pack(side=tk.LEFT)
        
        def add_new_page():
            page_frame, page_entries = create_page()
            all_entries.append((page_frame, page_entries))
            current_page[0] = len(all_entries) - 1
            change_page(0)
        
        # 儲存按鈕
        save_button = ttk.Button(
            button_frame,
            text="儲存變更",
            command=save_changes
        )
        save_button.pack(side=tk.RIGHT)
    
    def open_html_viewer(self):
        try:
            # 檢查 display_grid.html 是否存在
            html_path = "display_grid.html"
            if not os.path.exists(html_path):
                messagebox.showerror("錯誤", "找不到 display_grid.html 檔案")
                return
            
            # 啟動本地伺服器
            PORT = 8000
            Handler = http.server.SimpleHTTPRequestHandler
            
            def run_server():
                with socketserver.TCPServer(("", PORT), Handler) as httpd:
                    print(f"Server running at http://localhost:{PORT}")
                    httpd.serve_forever()
            
            # 在新行緒中啟動伺服器
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # 等待伺服器啟動
            time.sleep(1)
            
            # 使用預設瀏覽器開啟 HTML 檔案
            webbrowser.open(f'http://localhost:{PORT}/display_grid.html')
        
        except Exception as e:
            messagebox.showerror("錯誤", f"無法開啟檔案: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LinkExtractorGUI(root)
    root.mainloop() 