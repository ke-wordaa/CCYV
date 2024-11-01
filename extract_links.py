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

class LinkExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV 圖片連結提取器")
        self.root.geometry("800x600")
        
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
        
        # 結果顯示區域
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
    
    def show_right_click_menu(self, event):
        self.right_click_menu.tk_popup(event.x_root, event.y_root)
    
    def right_click_menu_action(self, action):
        try:
            if action == 'cut':
                self.root.focus_get().event_generate('<<Cut>>')
            elif action == 'copy':
                self.root.focus_get().event_generate('<<Copy>>')
            elif action == 'paste':
                self.root.focus_get().event_generate('<<Paste>>')
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
        # 空結果
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
        if isinstance(links, str):
            self.result_text.insert(tk.END, links)
            self.status_label.config(text="提取失敗")
            self.save_button.config(state=tk.DISABLED)
        else:
            if links:
                self.current_links = links  # 儲存連結
                for link in links:
                    self.result_text.insert(tk.END, link + "\n", "hyperlink")
                self.status_label.config(text=f"成功提取 {len(links)} 個圖片連結")
                self.save_button.config(state=tk.NORMAL)
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
            "links": []
        }
        
        try:
            # 讀取現有的 JSON 檔案
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    # 保留現有的連結，但移除已滿的部分
                    current_data["links"] = existing_data.get("links", [])[:8]  # 只保留前8個
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            
            # 添加新的連結（只添加第一個新連結）
            for link in self.current_links:
                if link not in current_data["links"]:
                    current_data["links"].insert(0, link)  # 在開頭插入新連結
                    break  # 只插入一個新連結就停止
            
            # 確保只有9個連結
            current_data["links"] = current_data["links"][:9]
            
            # 儲存更新後的資料
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            
            self.status_label.config(text=f"已更新 {filename}，共 {len(current_data['links'])} 個連結")
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
        
        # 連結列表框架
        links_frame = ttk.LabelFrame(main_frame, text="連結列表", padding="5")
        links_frame.pack(fill=tk.BOTH, expand=True)
        
        # 建立連結列表
        entries = []
        
        # 添加 load_links 函數定義
        def load_links():
            try:
                with open("cctv_links.json", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("links", [])
            except:
                return []
        
        # 創建共用的右鍵選單
        entry_menu = tk.Menu(editor_window, tearoff=0)
        entry_menu.add_command(label="剪下", command=lambda: editor_window.focus_get().event_generate('<<Cut>>'))
        entry_menu.add_command(label="複製", command=lambda: editor_window.focus_get().event_generate('<<Copy>>'))
        entry_menu.add_command(label="貼上", command=lambda: editor_window.focus_get().event_generate('<<Paste>>'))
        
        def show_entry_menu(event):
            widget = event.widget
            entry_menu.tk_popup(event.x_root, event.y_root)
        
        def create_link_row(link, index):
            row_frame = ttk.Frame(links_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            # 連結輸入框
            entry = ttk.Entry(row_frame)
            entry.insert(0, link)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entries.append(entry)
            
            # 綁定右鍵選單
            entry.bind('<Button-3>', show_entry_menu)
            
            # 測試按鈕
            test_button = ttk.Button(
                row_frame,
                text="測試",
                command=lambda: test_link(entry.get())
            )
            test_button.pack(side=tk.LEFT, padx=(5, 0))
            
            # 刪除按鈕
            def delete_row():
                row_frame.destroy()
                entries.remove(entry)
            
            delete_button = ttk.Button(
                row_frame,
                text="刪除",
                command=delete_row
            )
            delete_button.pack(side=tk.LEFT, padx=(5, 0))
        
        def test_link(url):
            try:
                webbrowser.open(url)
            except Exception as e:
                messagebox.showerror("錯誤", f"無法開啟連結: {str(e)}")
        
        def save_changes():
            try:
                # 收集所有未被刪除的連結
                new_links = []
                for entry in entries:
                    link = entry.get().strip()
                    if link:  # 如果連結不是空的
                        new_links.append(link)
                
                # 儲存到 JSON
                data = {
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                    "links": new_links
                }
                
                with open("cctv_links.json", 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("成功", "變更已儲存")
                editor_window.destroy()
                
            except Exception as e:
                messagebox.showerror("錯誤", str(e))
        
        def add_new_row():
            create_link_row("", len(entries))
        
        # 載入現有連結
        links = load_links()
        for i, link in enumerate(links):
            create_link_row(link, i)
        
        # 按鈕框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 新增按鈕
        add_button = ttk.Button(
            button_frame,
            text="新增連結",
            command=add_new_row
        )
        add_button.pack(side=tk.LEFT)
        
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
            
            # 在新執行緒中啟動伺服器
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