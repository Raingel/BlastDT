import os
import glob
import pandas as pd
from collections import defaultdict

def consolidate_forecasts():
    # 設定各預報版本資料夾與對應的預報欄位名稱
    forecast_dirs = {
        "prediction": "BlastDT",             # 假設版本1預報欄位為 BlastDT
        "prediction_BlastDT2": "BlastDT2",
        "prediction_BlastDT3": "BlastDT3"
    }
    
    output_dir = "prediction_daily"
    os.makedirs(output_dir, exist_ok=True)
    
    # 依各版本分開彙整
    for folder, forecast_col in forecast_dirs.items():
        if not os.path.exists(folder):
            print(f"目錄 {folder} 不存在，跳過。")
            continue
        
        # 使用字典以日期為 key，累積各筆資料（每一筆為一個 Series）
        daily_data = defaultdict(list)
        
        # 列出該資料夾內所有站號子目錄
        station_dirs = [d for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d))]
        for station in station_dirs:
            station_path = os.path.join(folder, station)
            # 找出所有 CSV 檔（假設檔名為年份，如 2020.csv）
            csv_files = glob.glob(os.path.join(station_path, "*.csv"))
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file)
                except Exception as e:
                    print(f"讀取 {csv_file} 時發生錯誤：{e}")
                    continue
                
                # 若日期欄名為 "Date"，則重新命名成 "日期"
                if "Date" in df.columns:
                    df = df.rename(columns={"Date": "日期"})
                elif "日期" not in df.columns:
                    print(f"檔案 {csv_file} 中找不到日期欄位，跳過。")
                    continue

                # 檢查該檔案是否包含此版本的預報欄位
                if forecast_col not in df.columns:
                    print(f"檔案 {csv_file} 中不含 {forecast_col} 欄位，跳過。")
                    continue
                
                # 只取所需欄位
                required_cols = ["站號", "站名", "日期", "lat", "lon", forecast_col]
                missing = [col for col in required_cols if col not in df.columns]
                if missing:
                    print(f"檔案 {csv_file} 缺少欄位 {missing}，跳過。")
                    continue
                
                df_subset = df[required_cols].copy()
                # 轉換日期格式為 YYYY-MM-DD（例如 "2024-12-04"）
                df_subset["日期"] = pd.to_datetime(df_subset["日期"], errors="coerce").dt.strftime("%Y-%m-%d")
                df_subset = df_subset[df_subset["日期"].notna()]  # 過濾日期不合法的列
                
                # 將每一列依日期累積起來
                for _, row in df_subset.iterrows():
                    date_str = row["日期"]
                    daily_data[date_str].append(row)
        
        # 將彙整後的資料依日期分檔輸出
        for date_str, rows in daily_data.items():
            df_out = pd.DataFrame(rows)
            # 排序（例如依站號）
            # 轉換站號為字串以確保排序一致性
            df_out["站號"] = df_out["站號"].astype(str)
            df_out.sort_values("站號", inplace=True)
            # 檔名格式：YYYYMMDD_版本名稱.csv  (例如：20241204_BlastDT3.csv)
            file_date = pd.to_datetime(date_str).strftime("%Y%m%d")
            output_file = os.path.join(output_dir, f"{file_date}_{forecast_col}.csv")
            # 調整輸出欄位順序
            df_out = df_out[["站號", "站名", "日期", "lat", "lon", forecast_col]]
            df_out.to_csv(output_file, index=False)
            print(f"已輸出彙整檔案：{output_file}")

if __name__ == "__main__":
    consolidate_forecasts()
