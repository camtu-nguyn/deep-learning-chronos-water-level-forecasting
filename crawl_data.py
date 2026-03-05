from playwright.sync_api import sync_playwright
from datetime import datetime
import pandas as pd
import re
import time

def crawl_reservoir_data():
    """
    Crawl dữ liệu hồ chứa thủy điện từ website EVN và lưu vào DataFrame
    """
    
    # Lấy thời gian hiện tại (chỉ đến giờ tròn)
    current_time = datetime.now()
    td_param = current_time.strftime("%d/%m/%Y %H:00")
    
    # Tạo URL với tham số thời gian hiện tại
    base_url = "https://phongchongthientai.evn.com.vn/PageHoChuaThuyDienEmbedEVN.aspx"
    url = f"{base_url}?td={td_param.replace(' ', '%20')}&vm=&lv=&hc=19-20"
    
    print(f"URL đang crawl: {url}")
    print(f"Thời gian: {td_param}")
    
    with sync_playwright() as p:
        # Khởi tạo browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # Truy cập trang web
            print("Đang tải trang...")
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Chờ một chút để trang load hoàn toàn
            time.sleep(3)
            
            # Lấy dữ liệu từ các hàng trong bảng myHeader
            reservoir_data = []
            
            try:
                # Kiểm tra xem div myHeader có tồn tại không
                header_div = page.locator("div#myHeader")
                if header_div.count() > 0:
                    print("✓ Tìm thấy div#myHeader")
                    
                    # Lấy tất cả các hàng tr trong tbody (bỏ qua header)
                    rows = page.locator("div#myHeader table tbody tr")
                    row_count = rows.count()
                    print(f"Tìm thấy {row_count} hàng")
                    
                    for i in range(row_count):
                        row = rows.nth(i)
                        row_class = row.get_attribute("class") or ""
                        
                        # Bỏ qua các hàng tiêu đề vùng (class="tralter")
                        if "tralter" in row_class:
                            continue
                        
                        # Lấy dữ liệu từ các cột
                        cells = row.locator("td")
                        cell_count = cells.count()
                        
                        if cell_count >= 11:  # Đảm bảo có đủ 11 cột
                            # Lấy tên hồ và thời gian đồng bộ từ cột đầu tiên
                            first_cell_html = cells.nth(0).inner_html()
                            
                            # Parse tên hồ từ thẻ <b>
                            name_match = re.search(r'<b>(.*?)</b>', first_cell_html)
                            reservoir_name = name_match.group(1).strip() if name_match else ""
                            
                            # Parse thời gian đồng bộ từ thẻ <small>
                            sync_match = re.search(r'<small>Đồng bộ lúc: (.*?)</small>', first_cell_html)
                            sync_time = sync_match.group(1).strip() if sync_match else ""
                            
                            # Lấy dữ liệu từ các cột còn lại
                            row_data = {
                                'ten_ho': reservoir_name,
                                'dong_bo_luc': sync_time,
                                'thoi_diem': cells.nth(1).inner_text().strip(),
                                'htl': cells.nth(2).inner_text().strip(),
                                'hdbt': cells.nth(3).inner_text().strip(),
                                'hc': cells.nth(4).inner_text().strip(),
                                'qve': cells.nth(5).inner_text().strip(),
                                'sum_qx': cells.nth(6).inner_text().strip(),
                                'qxt': cells.nth(7).inner_text().strip(),
                                'qxm': cells.nth(8).inner_text().strip(),
                                'ncxs': cells.nth(9).inner_text().strip(),
                                'ncxm': cells.nth(10).inner_text().strip()
                            }
                            
                            reservoir_data.append(row_data)
                            print(f"✓ Đã lấy dữ liệu hồ: {reservoir_name}")
                    
                else:
                    print("⚠ Không tìm thấy div#myHeader")
                    
            except Exception as e:
                print(f"Lỗi khi lấy dữ liệu bảng: {e}")
            
            return reservoir_data
            
        except Exception as e:
            print(f"Lỗi khi crawl dữ liệu: {e}")
            return []
            
        finally:
            browser.close()

def create_dataframe(data):
    """
    Tạo DataFrame từ dữ liệu crawl được
    """
    if not data:
        print("Không có dữ liệu để tạo DataFrame")
        return pd.DataFrame()
    
    # Tạo DataFrame
    df = pd.DataFrame(data)
    
    # Đổi tên cột cho dễ hiểu
    column_names = {
        'ten_ho': 'Tên hồ',
        'dong_bo_luc': 'Đồng bộ lúc',
        'thoi_diem': 'Thời điểm',
        'htl': 'H_tl (m)',
        'hdbt': 'H_dbt (m)', 
        'hc': 'H_c (m)',
        'qve': 'Q_ve (m³/s)',
        'sum_qx': 'ΣQ_x (m³/s)',
        'qxt': 'Q_xt (m³/s)',
        'qxm': 'Q_xm (m³/s)',
        'ncxs': 'N_cxs',
        'ncxm': 'N_cxm'
    }
    
    df = df.rename(columns=column_names)
    
    # Chuyển đổi các cột số về kiểu float (nếu có thể)
    numeric_columns = ['H_tl (m)', 'H_dbt (m)', 'H_c (m)', 'Q_ve (m³/s)', 
                      'ΣQ_x (m³/s)', 'Q_xt (m³/s)', 'Q_xm (m³/s)', 'N_cxs', 'N_cxm']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

def save_dataframe(df, filename="reservoir_data.csv"):
    """
    Lưu DataFrame vào file CSV
    """
    try:
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✓ Đã lưu DataFrame vào file: {filename}")
    except Exception as e:
        print(f"Lỗi khi lưu file: {e}")

def print_dataframe_info(df):
    """
    Hiển thị thông tin DataFrame
    """
    if df.empty:
        print("DataFrame rỗng")
        return
    
    print("\n" + "="*60)
    print("THÔNG TIN DATAFRAME")
    print("="*60)
    print(f"Số hàng: {len(df)}")
    print(f"Số cột: {len(df.columns)}")
    print(f"Các cột: {list(df.columns)}")
    
    print("\nDỮ LIỆU MẪU:")
    print("-" * 60)
    print(df.head())
    
    print("\nTHỐNG KÊ MÔ TẢ:")
    print("-" * 60)
    print(df.describe())

if __name__ == "__main__":
    print("BẮT ĐẦU CRAWL DỮ LIỆU HỒ CHỨA THỦY ĐIỆN")
    print("="*50)
    
    # Crawl dữ liệu
    data = crawl_reservoir_data()
    
    if data:
        # Tạo DataFrame
        df = create_dataframe(data)
        
        if not df.empty:
            # Lưu DataFrame vào file CSV
            save_dataframe(df)
            
            # Hiển thị thông tin DataFrame
            print_dataframe_info(df)
            
            print("\n" + "="*50)
            print("CRAWL VÀ TẠO DATAFRAME HOÀN THÀNH!")
            
            # Trả về DataFrame để sử dụng
            print(f"\nBạn có thể sử dụng DataFrame với {len(df)} hàng dữ liệu")
        else:
            print("Không thể tạo DataFrame từ dữ liệu")
    else:
        print("CRAWL THẤT BẠI!")