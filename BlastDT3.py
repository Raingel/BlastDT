# Description: This is a notebook to predict the occurrence of rice blast disease using formula from the NIAN project
"""
Version 3: Risk calculation logic:
For a given day, if all conditions are met then the day is high risk:
  1. Daily maximum temperature (TxMaxAbs) >= 20.7°C
  2. Daily mean temperature (Tx) < 30.8°C
  3. Daily mean relative humidity (RH) >= 74%
Contact: Jie-Hao, Ou  allenstorm2005@gmail.com
Be aware that the weather data is from the github repo, which might not be the most updated data.
"""
import pandas as pd
import os
from datetime import datetime, timedelta

class nian:
    def __init__(self, RH_threshold=74, T_threshold_upper=30.8, T_threshold_lower=20.7):
        """
        Initialize predictor with parameters for version 3:
          RH_threshold: daily mean RH must be >= this value (default 74)
          T_threshold_upper: daily mean temperature must be < this value (default 30.8)
          T_threshold_lower: daily maximum temperature must be >= this value (default 20.7)
        """
        self.RH_threshold = RH_threshold
        self.T_threshold_upper = T_threshold_upper
        self.T_threshold_lower = T_threshold_lower

    def get_daily_weather(self, sta_no=466940, start=datetime(2021,8,16), end=datetime(2022,9,13), raw=False):
        """
        Retrieve daily weather data from local folder (下載資料前請先執行 git clone 指令下載 weather_data)
        """
        start_year = start.year
        if start.month == 1:
            start_year = start.year - 1
        end_year = end.year
        if end.month == 12:
            end_year = end.year + 1

        df = pd.DataFrame()
        for year in range(start_year, end_year + 1):
            RESOURCE = f"./weather_data/data/{sta_no}/{sta_no}_{year}_daily.csv"
            try:
                temp_df = pd.read_csv(RESOURCE)
                df = pd.concat([df, temp_df]) if not df.empty else temp_df
            except Exception as e:
                base_dir = os.getcwd()
                weather_data_dir = os.path.join(base_dir, "weather_data")
                weather_data_contents = os.listdir(weather_data_dir) if os.path.exists(weather_data_dir) else []
                print("Error: Cannot retrieve data from {}".format(RESOURCE), e)
                print("Current base directory:", base_dir)
                print("Contents of weather_data directory:", weather_data_contents)
        # 轉換日期欄位並補齊缺漏日期
        try:
            df['Unnamed: 0'] = pd.to_datetime(df['Unnamed: 0'])
            df = df.set_index('Unnamed: 0')
            df = df[~df.index.duplicated(keep='first')]
            df = df.reindex(pd.date_range(start=df.index.min(), end=df.index.max()))
            df['Unnamed: 0'] = df.index.astype(str)
            df.reset_index(drop=True, inplace=True)
        except Exception as e:
            print("Error: Corrupted date column", e)
            return pd.DataFrame()

        # 將異常數值轉為 NaN，並線性補值
        df = df.replace(-9.8, float('NaN'))
        df = df.replace(-99.7, float('NaN'))
        num_cols = df.select_dtypes(include=['float64', 'int64']).columns
        df[num_cols] = df[num_cols].apply(lambda x: x.mask(x < -99))
        df = df.interpolate(method='linear', axis=0, limit_area='inside')
        # 保留指定日期範圍內的資料
        df = df[(df['Unnamed: 0'] >= start.strftime("%Y-%m-%d")) & (df['Unnamed: 0'] <= end.strftime("%Y-%m-%d"))]
        df.reset_index(drop=True, inplace=True)
        return df

    def load_weather_station(self):
        """
        從遠端取得氣象站資料
        """
        return pd.read_csv("https://raw.githubusercontent.com/Raingel/weather_station_list/main/data/weather_sta_list.csv")
    
    def BlastDT3(self, df):
        """
        根據第三版邏輯計算稻瘟病高風險日期：
         - 日高溫 (TxMaxAbs) >= self.T_threshold_lower (20.7°C)
         - 日均溫 (Tx) < self.T_threshold_upper (30.8°C)
         - 日均濕度 (RH) >= self.RH_threshold (74%)
        預期輸入的 dataframe 需包含欄位：
         - TxMaxAbs: 日高溫
         - Tx: 日均溫
         - RH: 日均濕度
        本函式會在 df 中新增下列欄位：
         - TxMaxAbs_condition: 判斷 TxMaxAbs 是否達標
         - Tx_condition: 判斷 Tx 是否達標
         - RH_condition: 判斷 RH 是否達標
         - BlastDT3: 當三項條件皆成立時為 True，否則為 False
        """
        # 轉型為 float
        df['TxMaxAbs'] = df['TxMaxAbs'].astype(float)
        df['Tx'] = df['Tx'].astype(float)
        df['RH'] = df['RH'].astype(float)
        
        # 評估各項條件
        df['TxMaxAbs_condition'] = df['TxMaxAbs'] >= self.T_threshold_lower
        df['Tx_condition'] = df['Tx'] < self.T_threshold_upper
        df['RH_condition'] = df['RH'] >= self.RH_threshold
        
        # 當三項條件皆成立時，該日為高風險
        df['BlastDT3'] = df['TxMaxAbs_condition'] & df['Tx_condition'] & df['RH_condition']
        
        return df

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--RH_THRESHOLD", type=float, default=74, help="設定日均濕度下限 (>=74)")
    parser.add_argument("--T_THRESHOLD_UPPER", type=float, default=30.8, help="設定日均溫上限 (<30.8)")
    parser.add_argument("--T_THRESHOLD_LOWER", type=float, default=20.7, help="設定日高溫下限 (>=20.7)")
    parser.add_argument("--START_YEAR", type=int, default=2020, help="起始年份")
    parser.add_argument("--END_YEAR", type=int, default=datetime.now().year, help="結束年份")
    parser.add_argument("--OUTPUT_DIR", type=str, default="prediction_BlastDT3", help="結果輸出資料夾")
    args, _ = parser.parse_known_args()

    # 設定參數與年份區間
    RH_THRESHOLD = args.RH_THRESHOLD
    T_THRESHOLD_UPPER = args.T_THRESHOLD_UPPER
    T_THRESHOLD_LOWER = args.T_THRESHOLD_LOWER
    SPAN = (args.START_YEAR, args.END_YEAR)
    OUTPUT_DIR = args.OUTPUT_DIR
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 初始化風險預測器 (第三版邏輯)
    predictor = nian(RH_threshold=RH_THRESHOLD, T_threshold_upper=T_THRESHOLD_UPPER, T_threshold_lower=T_THRESHOLD_LOWER)
    
    # 讀取氣象站資料
    stations = predictor.load_weather_station()
    # 排除 C1 站（僅有雨量）
    stations = stations[stations['站號'].str[0:2] != "C1"]
    # 排除已撤站資料
    stations = stations[stations['撤站日期'].isna() == True]

    for i, row in stations.iterrows():
        sta_no = row['站號']
        sta_name = row['站名']
        print("Processing station {} ({}) for years {}".format(sta_no, sta_name, SPAN))
        for year in range(SPAN[0], SPAN[1] + 1):
            try:
                # 由於不再需要滾動視窗，因此直接取該年度1/1至12/31的資料
                df = predictor.get_daily_weather(sta_no, datetime(year, 1, 1), datetime(year, 12, 31))
                df_p = predictor.BlastDT3(df)
            except Exception as e:
                print("Error: Cannot retrieve data for station {}".format(sta_no), e)
                continue
            os.makedirs(f"{OUTPUT_DIR}/{sta_no}", exist_ok=True)
            df_p['Date'] = df_p['Unnamed: 0']
            # 輸出所需欄位：包含計算結果與各條件
            df_p = df_p[['Date', 'BlastDT3', 'TxMaxAbs', 'TxMaxAbs_condition', 'Tx', 'Tx_condition', 'RH', 'RH_condition']]
            df_p["站號"] = sta_no
            df_p["站名"] = sta_name
            df_p["lat"] = row["緯度"]
            df_p["lon"] = row["經度"]
            df_p.to_csv(f"{OUTPUT_DIR}/{sta_no}/{year}.csv", index=False)
