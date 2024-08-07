#Description: This is a notebook to predict the occurrence of rice blast disease using formula from the NIAN project
"""
Though this work can be easily done without pandas, I use pandas to make the code more readable
Contact: Jie-Hao, Ou  allenstorm2005@gmail.com
Be aware that the weather data is from the github repo, which might not be the most updated data
"""
import pandas as pd
import os
from datetime import datetime, timedelta
#from git import Repo
import shutil
class nian:
    #Some basic parameters
    #RH_threshold: Set the lower bound of relative humidity for rice blast disease
    #T_threshold: Set the upper bound of temperature for rice blast disease
    #windows_length: How many consecutive days to be considered as a period
    def __init__(self, RH_threshold = 77, T_threshold_upper = 30.7, T_threshold_lower = 20.7, windows_length = 3):
        self.RH_threshold = RH_threshold
        self.T_threshold_upper = T_threshold_upper
        self.T_threshold_lower = T_threshold_lower
        self.WINDOWS_LENGTH = windows_length
    
    #This function is to retrieve the weather data from the github repo
    def get_daily_weather(self, sta_no = 466940, start = datetime(2021,8,16), end = datetime (2022,9,13), raw = False):
        #When raw = True is set, the function will return the raw data from the database. 
        #There might be some missing data (-9.8 and -99.7) in the raw data. Use with caution.
        start_year = start.year
        if start.month == 1:
            start_year = start.year - 1
        end_year = end.year
        if end.month == 12:
            end_year = end.year + 1

        df = pd.DataFrame()  # Initialize df before the loop
        for year in range(start_year, end_year + 1):
            RESOURCE = f"./weather_data/data/{sta_no}/{sta_no}_{year}_daily.csv"
            try:
                temp_df = pd.read_csv(RESOURCE)
                df = pd.concat([df, temp_df]) if not df.empty else temp_df
            except Exception as e:
                base_dir = os.getcwd()
                weather_data_dir = os.path.join(base_dir, "weather_data")
                weather_data_contents = os.listdir(weather_data_dir)
                print("Error: Cannot retrieve data from {}".format(RESOURCE), e)
                print("Current base directory:", base_dir)
                print("Contents of weather_data directory:", weather_data_contents)
        #Make sure there is no missing date in the dataframe
        try:
            df['Unnamed: 0'] = pd.to_datetime(df['Unnamed: 0'])
            df = df.set_index('Unnamed: 0')
            #remove duplicated index
            df = df[~df.index.duplicated(keep='first')]
            df.reindex(pd.date_range(start=df.index.min(), end=df.index.max()))
            df['Unnamed: 0'] = df.index.astype(str)
            df.reset_index(drop=True, inplace=True)
        except:
            print("Error: Corrupted date column")
            return pd.DataFrame()


        #replace -9.8, -99.7 or value smaller than -99 with NaN
        df = df.replace(-9.8, float('NaN'))
        df = df.replace(-99.7, float('NaN'))
        #replace value smaller than -100 with NaN in all numeric columns
        df[df.select_dtypes(include=['float64','int64']).columns] = df[df.select_dtypes(include=['float64','int64']).columns].apply(lambda x: x.mask(x < -99))
        #Interpolate all vertical columns
        #Note: Interpolation might significantly change the data. Use with caution.
        df = df.interpolate(method='linear', axis=0, limit_area='inside')
        #Preserve only desired date range
        df = df[(df['Unnamed: 0'] >= start.strftime("%Y-%m-%d")) & (df['Unnamed: 0'] <= end.strftime("%Y-%m-%d"))]
        df.reset_index(drop=True, inplace=True)
        return df

    #This function is to retrieve the weather station list from the github repo
    def load_weather_station(self):
        return pd.read_csv("https://raw.githubusercontent.com/Raingel/weather_station_list/main/data/weather_sta_list.csv")
        
    def BlastDT2(self, df):
        """
        input df: pandas dataframe with the following columns:
            TxMaxAbs: Daily maximum temperature
            RH: Daily relative humidity
        ##Also make sure the date is consecutive and in the correct format
        """
        df.loc[0,'TxMaxAbs'] = float("NaN")
        #check if daily TxMaxAbs >= T_threshold_lower
        df['TxMaxAbs'] = df['TxMaxAbs'].astype(float)
        df['TxMaxAbs_condition'] = df['TxMaxAbs'] >= self.T_threshold_lower
        #if "TxMaxAbs" is NaN, then set "TxMaxAbs_nian" to NaN
        df['TxMaxAbs_condition'] = df['TxMaxAbs_condition'].where(df['TxMaxAbs'].notnull(), float("NaN"))

        #check if Tx <= T_threshold_upper
        df['Tx'] = df['Tx'].astype(float)
        df['Tx_condition'] = df['Tx'] <= self.T_threshold_upper
        #if "Tx" is NaN, then set "Tx_nian" to NaN
        df['Tx_condition'] = df['Tx_condition'].where(df['Tx'].notnull(), float("NaN"))


        #check if daily RH > RH_threshold, if RH is Nan then set to Nan
        df['RH'] = df['RH'].astype(float)
        df['RH_condition'] = df['RH'] >= self.RH_threshold
        #if "RH" is NaN, then set "RH_nian" to NaN
        df['RH_condition'] = df['RH_condition'].where(df['RH'].notnull(), float("NaN"))
        #check if there are 3 consecutive days with TxMaxAbs > T_threshold and RH > RH_threshold
        df['TxMaxAbs_condition_rolling'] = df['TxMaxAbs_condition'].rolling(self.WINDOWS_LENGTH).apply(lambda x: all(x), raw=True)
        df['Tx_condition_rolling'] = df['Tx_condition'].rolling(self.WINDOWS_LENGTH).apply(lambda x: all(x), raw=True)
        df['RH_condition_rolling'] = df['RH_condition'].rolling(self.WINDOWS_LENGTH).apply(lambda x: all(x), raw=True)


        #if TxMaxAbs_nian_rolling, Tx_nian_rolling and RH_nian_rolling are all True, then set "BLASTDT2" to True
        df['BlastDT2'] = (df['TxMaxAbs_condition_rolling']==1) & (df['Tx_condition_rolling']==1) & (df['RH_condition_rolling']==1)
        #if "TxMaxAbs_condition_rolling" or "Tx_condition_rolling" or "RH_condition_rolling" is NaN, then set "BLASTDT2" to NaN
        df['BlastDT2'] = df['BlastDT2'].where(df['TxMaxAbs_condition_rolling'].notnull(), float("NaN"))
        df['BlastDT2'] = df['BlastDT2'].where(df['Tx_condition_rolling'].notnull(), float("NaN"))
        df['BlastDT2'] = df['BlastDT2'].where(df['RH_condition_rolling'].notnull(), float("NaN"))
    

        return df

import argparse
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--RH_THRESHOLD", type=float, default=77, help="Set the lower bound of relative humidity for rice blast disease")
    parser.add_argument("--T_THRESHOLD_UPPER", type=float, default=30.7, help="Set the upper bound of temperature for rice blast disease")
    parser.add_argument("--T_THRESHOLD_LOWER", type=float, default=20.7, help="Set the lower bound of temperature for rice blast disease")
    parser.add_argument("--WINDOWS_LENGTH", type=int, default=1, help="Rolling windows length")
    parser.add_argument("--START_YEAR", type=int, default=2020, help="Start from which year")
    parser.add_argument("--END_YEAR", type=int, default=datetime.now().year, help="End at which year")
    parser.add_argument("--OUTPUT_DIR", type=str, default="prediction_BlastDT2", help="Output directory")
    args, _ = parser.parse_known_args()
    #Download weather data
    #if os.path.exists("weather_data"):
    #    shutil.rmtree("weather_data")
    #Repo.clone_from("https://github.com/Raingel/historical_weather.git", "weather_data")
    #Set custom parameters HERE
    RH_THRESHOLD = args.RH_THRESHOLD   #Set the lower bound of relative humidity for rice blast disease
    T_THRESHOLD_UPPER = args.T_THRESHOLD_UPPER   #Set the upper bound of temperature for rice blast disease
    T_THRESHOLD_LOWER = args.T_THRESHOLD_LOWER   #Set the lower bound of temperature for rice blast disease
    WINDOWS_LENGTH = args.WINDOWS_LENGTH   #Rolling windows length
    SPAN = (args.START_YEAR, args.END_YEAR)   #Set the year range
    OUTPUT_DIR = args.OUTPUT_DIR   #Set the output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    #Initialize the predictor
    predictor = nian(RH_THRESHOLD, T_THRESHOLD_UPPER, T_THRESHOLD_LOWER, WINDOWS_LENGTH)

    #Load weather station
    stations = predictor.load_weather_station()
    #Filter out the C1 stations (rainfall only)
    stations = stations[stations['站號'].str[0:2] != "C1"]
    #Filter out the stations that are not in service
    stations = stations[stations['撤站日期'].isna() == True]

    for i, row in stations[:].iterrows():
        sta_no = row['站號']
        sta_name = row['站名']
        print("Processing {} for year {}".format(sta_no, SPAN))
        for year in range(SPAN[0], SPAN[1]+1):
            try:
                df = predictor.get_daily_weather(sta_no, datetime(year,1,1) - timedelta(days = WINDOWS_LENGTH), datetime(year,12,31))
                df_p = predictor.BlastDT2(df)
            except Exception as e:

                print("Error: Cannot retrieve data for station {}".format(sta_no),e)
                continue
            os.makedirs("{}/{}".format(OUTPUT_DIR,sta_no), exist_ok=True)
            df_p['Date'] = df_p['Unnamed: 0']
            df_p = df_p[['Date', 'BlastDT2', 'Tx', 'Tx_condition', 'Tx_condition_rolling', 'TxMaxAbs', 'TxMaxAbs_condition', 'TxMaxAbs_condition_rolling', 'RH',  'RH_condition',  'RH_condition_rolling']]
            df_p["站號"] = sta_no
            df_p["站名"] = sta_name
            df_p["lat"] = row["緯度"]
            df_p["lon"] = row["經度"]
            df_p.to_csv("{}/{}/{}.csv".format(OUTPUT_DIR, sta_no,year), index=False)


    #if os.path.exists("weather_data"):
    #    shutil.rmtree("weather_data")
