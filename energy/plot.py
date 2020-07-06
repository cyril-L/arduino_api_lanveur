import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.optimize

pd.plotting.register_matplotlib_converters()

df = pd.read_csv("2020-may-june.csv")

SAMPLE_RATE = 60
V_STORED_WATER = 0.3  # m³
T_AMBIANT = 19  # °C


def summary(df):
    print(df.head())
    print(df.columns)
    print(df.dtypes)
    print(df.describe())


def model_stored_temp(df):
    return (df['Teb'] + df['Teh']) / 2


df['T_stored'] = model_stored_temp(df)


def model_flow(df, var):
    return df[var].diff() / SAMPLE_RATE


df['F_solar'] = model_flow(df, 'Vep')
df['F_hot_water'] = model_flow(df, 'Vecs')


def model_cooling_power(temp_inside, temp_outside, UA):
    return (temp_outside - temp_inside) * UA  # W


# def extract_cooling_samples(df):

df['cooling_start'] = float("nan")

summary(df)

decreasing_since_t = None

df['dT_stored'] = df['T_stored'].diff()

for index, row in df.iterrows():
    is_flowing = row['F_solar'] != 0 or row['F_hot_water'] != 0
    if row['dT_stored'] <= 0 and not is_flowing:
        if decreasing_since_t is None:
            decreasing_since_t = row['clock']
        df.loc[index, 'cooling_start'] = decreasing_since_t
    else:
        decreasing_since_t = None

df['cooling_time'] = df['clock'] - df['cooling_start']

# extract_cooling_samples(df)

summary(df)

# def extract_cooling_samples(df):

#     df['cooling_start']
#     df['cooling_time']

#     cooling_samples = []
#     decreasing_since_id = None
#     decreasing_since_t = None
#     last_stored_temp = df.iloc[0]['T_stored']
#     for index, row in df.iterrows():
#         temp = row['T_stored']
#         time = row['clock']
#         is_flowing = row['F_solar'] != 0 or row['F_hot_water'] != 0
#         if temp <= last_stored_temp and not is_flowing:
#             if decreasing_since_id is None:
#                 decreasing_since_t = time
#                 decreasing_since_id = index
#         else:
#             if decreasing_since_id is not None and time - decreasing_since_t > 3600:
#                 cooling_samples.append(df.iloc[decreasing_since_id:index-1])
#             decreasing_since_id = None
#         last_stored_temp = row['T_stored']
#     return cooling_samples

# print(len(extract_cooling_samples(df)))

df['dT_stored_SMA'] = df['dT_stored'].rolling(window=10).mean()

# sns.relplot(x='cooling_time', y="dT_stored_SMA", data=df)

df_cooling = df.dropna(subset=['cooling_start'])

print(df_cooling['dT_stored_SMA'].median())

sns.distplot(df_cooling['dT_stored_SMA'])

# sns.relplot(x='cooling_time', y="T_stored", kind="line", hue='cooling_start', data=df)

plt.show()

df_temps = pd.melt(df, id_vars=['clock'], value_vars=[ c for c in df.columns if c[0] == 'T'], var_name='label', value_name='temperature')

summary(df_temps)

sns.relplot(x='clock', y="temperature", kind="line", hue="label", data=df_temps)
# sns.relplot(x="total_bill", y="tip", data=tips);

# Set the width and height of the figure
# plt.figure(figsize=(16,6))

# Line chart showing how FIFA rankings evolved over time 
# sns.relplot(data=df, x="clock", y="Teb")
#sns.lineplot(data=df, x="clock", y="Teh")

plt.show()
