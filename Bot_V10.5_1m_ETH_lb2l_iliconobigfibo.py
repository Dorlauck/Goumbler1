from lib2to3.pytree import convert
import pandas as pd
import io 
import os
import sys
import schedule
import peakutils
import ta
import calendar
import talib
import time
import matplotlib.pyplot as plt
import discord
from discord.ext import commands
import requests
from binance.client import Client  # Assurez-vous d'avoir installé la bibliothèque python-binance
import sqlite3
from datetime import date, datetime,timedelta

# Planifiez la fermeture du programme à l'heure spécifiée
def fermer_programme():
    print("Fermeture du programme à", time.strftime("%H:%M:%S"))
    sys.exit()
heure_fermeture = "05:59"
schedule.every().day.at(heure_fermeture).do(fermer_programme)

interval = '1m'      # Définit l'intervalle sur lequel Goumbler va prendre des trades
lookback_period = 2  # Définir le lookback_period comme une variable globale
symbol = 'ETHUSDT'   # Crypto sur lequel Goumbler va prendre des trades
risque = 0.1         # Pourcentage du capital risqué par trade
short_window=2       # Paramètre qui détermine le nombre de bougies à analyser pour l'indicateur MACDs
long_window=5        # Paramètre qui détermine le nombre de bougies à analyser pour l'indicateur MACDs
Fibo_correct = False # Vérifie si le fibo est correct 
trend = None         # Variable de tendance
discord_captainhook_de_noobs= 'https://discord.com/api/webhooks/1188970591001247884/lQEieU7ndSTsMpifoGMorE82l8pLrq1GHlXCQsC9J0or8RAY6RZmaijSCcPxYCJXNxrW'
data_base = 'Data_ETH_Iliconobigfibo.sqlite'
conn = sqlite3.connect(data_base)

# Création d'un objet cursor pour exécuter des commandes SQL
cursor = conn.cursor()

# Création de la table Transactions
cursor.execute('''
CREATE TABLE IF NOT EXISTS Transactions (
    transaction_id INTEGER PRIMARY KEY,
    date TEXT,
    date_jour TEXT,
    date_heure TEXT,
    type TEXT,
    rr REAL,
    gain_counter REAL,
    trade_counter REAL,
    lose_streak REAL,
    win_streak REAL,
    winrate REAL,
    startfibo TEXT,
    
    remarks TEXT,
    capital REAL
)
''')

# Fermeture de la connexion à la base de données
conn.close()

######################## ajout/mise à jour #########################"


def record_transaction(date_time, type,rr,gain_counter,trade_counter,lose_streak,win_streak,date_last_high,date_last_low, remarks=''):

    if trend == 'Bullish':
        formatted_date_start = date_last_low.strftime('%Y-%m-%d %H:%M:%S')
    if trend == 'Bearish':
        formatted_date_start = date_last_high.strftime('%Y-%m-%d %H:%M:%S')
    formatted_date = date_time.strftime('%Y-%m-%d %H:%M:%S')
    formatted_date_jour = date_time.strftime('%Y-%m-%d')
    convert_formated_date_jour = datetime.strptime(formatted_date_jour,'%Y-%m-%d')
    fully_formatted_date_jour = convert_formated_date_jour.weekday()

      # Obtenir le nom du jour de la semaine
    day_of_week = calendar.day_name[fully_formatted_date_jour]
    adjusted_date_hour = date_time + timedelta(hours=1-6)
    formatted_date_heure = adjusted_date_hour.strftime('%H:%M') 
    conn = sqlite3.connect(data_base)
    cursor = conn.cursor()
    cursor.execute(f'''
    INSERT INTO Transactions (date,date_jour, date_heure, type,rr, gain_counter, trade_counter,lose_streak,win_streak,winrate,startfibo, remarks,capital)
    VALUES ('{formatted_date}','{day_of_week}','{formatted_date_heure}', '{type}','{rr}', '{gain_counter}', '{trade_counter}','{lose_streak}','{win_streak}','{(gain_counter/trade_counter)*100}','{formatted_date_start}','{remarks}','{capital}');
    ''', )
    conn.commit()
    conn.close()

# Liaison à l'API Binance pour extraire les données des 100(limit) bougies
def get_binance_candlestick_data(symbol, limit=100):
    # Assurez-vous d'avoir votre clé API et votre clé secrète
    api_key = 'LzYtHZsJuTkDior1zJ6EZ1c7lQT3Tmw5BcVTW5RD7FiPHW7eHO89Qlj2U1Xhcoxa'
    api_secret = 'CUPl1owodqKkSVOMRVVi7tqYXuvgVxRKJZwAZJmgeffIX7XGlgmb1mW0uuBWXPG6'
    
    client = Client(api_key, api_secret)
    interval = globals()['interval']  # Access the global interval variable
    # Récupérer les données de bougie depuis l'API Binance
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)

    # Convertir les données en DataFrame pandas
    data = pd.DataFrame(klines, columns=['Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close time', 'Quote asset volume', 'Number of trades', 'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'])
    

    # Formater les colonnes
    data['Open time'] = pd.to_datetime(data['Open time'], unit='ms')
    data['Close time'] = pd.to_datetime(data['Close time'], unit='ms')

    # Ajouter la colonne 'Date'
    data['Date'] = data['Open time'].dt.floor('Min')  # Utiliser l'heure d'ouverture comme date

     # Sélectionner uniquement les colonnes nécessaires
    data = data[['Date', 'Open', 'High', 'Low', 'Close']]

     # Convertir les colonnes nécessaires en types numériques
    numeric_columns = ['Open', 'High', 'Low', 'Close']
    data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric, errors='coerce')

     # Gérer les valeurs manquantes en les remplaçant par la moyenne (vous pouvez choisir une autre méthode)
    data.fillna(data.mean(), inplace=True)

    return data

#Liaison à l'API Discord pour envoyer des messages 
def send_discord_message(message, color=""):
    discord_webhook_url = discord_captainhook_de_noobs
    # Ajoutez la couleur au message en utilisant le balisage Markdown
    if color.lower() == "rouge":
        message = f"```diff\n- {message}\n```"
    elif color.lower() == "vert":
        message = f"```fix\n{message}\n```"
    payload = {
        "content": message
    }
    requests.post(discord_webhook_url, json=payload)
    
#Liaison à l'API Discord pour envoyer des messages dans un autre channel gain/perte
def send_discord_message_gain_perte(message, color=""):
    discord_webhook_url = discord_captainhook_de_noobs
    # Ajoutez la couleur au message en utilisant le balisage Markdown
    if color.lower() == "rouge":
        message = f"```diff\n- {message}\n```" 
    elif color.lower() == "vert":
        message = f"```fix\n{message}\n```"
    payload = {
        "content": message
    }
    requests.post(discord_webhook_url, json=payload)

#Liaison à l'API Discord pour envoyer des images (Graphiques)
def send_discord_message_with_image(message, image_path):
    # Obtenez le chemin absolu du dossier du script
    script_folder = os.path.dirname(os.path.abspath(__file__))
    
    # Joignez le chemin relatif à l'emplacement du script
    image_path = os.path.join(script_folder, image_path)

    discord_webhook_url = discord_captainhook_de_noobs #Le webhook est le lien qui lie le script à un channel Discord
    files = {'file': (image_path, open(image_path, 'rb'))}
    payload = {
        "content": message
    }
    requests.post(discord_webhook_url, data=payload, files=files)

#Identifie le major High and Low et retourne les last
def identify_major_highs_lows(data):
    """
    Identify major highs and lows in a financial time series.

    Parameters:
    - data: Pandas DataFrame with 'Open', 'High', 'Low', 'Close' columns.
    - lookback_period: Number of previous candles to consider for identifying major highs/lows.
    - threshold: Minimum percentage change to consider a point as a major high/low.

    Returns:
    - major_highs: List of indices representing major highs.
    - major_lows: List of indices representing major lows.
    - last_low: Index of the last major low.
    - last_high: Index of the last major high.
    """

    # Calculate percentage change in close prices
    data['Close_change'] = data['Close'].pct_change() * 100

    # Initialize lists to store major highs and lows
    major_highs = []
    major_lows = []

    # Initialize variables for the last major low and high
    last_low = None
    last_high = None

    # Variable to track if the last point was a high or a low

    for i in range(lookback_period, len(data) - lookback_period):

        # Conditions pour trouver un low : faire en sorte que le low de la bougie analysé est plus low que les 2low d'après et les 2 low d'avant pareil pour les closes(sijamais il n'y a pas de mèche)
        if (
            data['Low'].iloc[i] <= data['Low'].iloc[i-1] and
            data['Low'].iloc[i] <= data['Low'].iloc[i+1] and
            data['Low'].iloc[i] <= data['Low'].iloc[i-2] and
            data['Low'].iloc[i] <= data['Low'].iloc[i+2] and
            data['Low'].iloc[i] <= data['Close'].iloc[i-1] and
            data['Low'].iloc[i] <= data['Close'].iloc[i+1] and
            data['Low'].iloc[i] <= data['Close'].iloc[i-2] and
            data['Low'].iloc[i] <= data['Close'].iloc[i+2]

            
        ):
            major_lows.append(i) # Ajoute dans la liste des major LOW si conditions vérifiés
            last_low = i         # définit le last low avec le dernier major Low retourné

        # Conditions pour trouver un low : faire en sorte que le low de la bougie analysé est plus low que les 2low d'après et les 2 low d'avant pareil pour les closes(sijamais il n'y a pas de mèche)
        if (
            data['High'].iloc[i] >= data['High'].iloc[i-1] and
            data['High'].iloc[i] >= data['High'].iloc[i+1] and
            data['High'].iloc[i] >= data['High'].iloc[i-2] and
            data['High'].iloc[i] >= data['High'].iloc[i+2] and
            data['High'].iloc[i] >= data['Close'].iloc[i-1] and
            data['High'].iloc[i] >= data['Close'].iloc[i+1] and
            data['High'].iloc[i] >= data['Close'].iloc[i-2] and
            data['High'].iloc[i] >= data['Close'].iloc[i+2] 
        ):
            
            major_highs.append(i) # Ajoute dans la liste des major high si conditions vérifiés
            last_high = i         # Définit le last high avec le dernier major high retourné
    return major_highs, major_lows, last_low, last_high,

# Fonction qui dessine le Fibo: les lows et highs: la tendance vert quand c'est bullish et rouge quand c'est bearish
def plot_fibonacci_and_zigzag(data,first_trend, trend, major_highs, major_lows, last_low, last_high, save_path=r"C:\Users\Dytoc\Desktop\Goumbler\Graphes Bot", color_period=2):
    
    # Calculate Fibonacci retracement levels
    fib_levels = [0, 0.5, 0.62, 0.79, 1]

    
    Fibo_reverese = False
    # Check if the current trend is bullish or bearish
    if trend == 'Bearish':
        if data.index[last_low] > data.index[last_high]: # le dernier low doit être placé après le dernier high 
            retracement_levels = [
                data['Low'].iloc[last_low] + level * (data['High'].iloc[last_high] - data['Low'].iloc[last_low]) for level in fib_levels # calcul niveau de retracement 
            ]
            Fibo_correct = True # renvoie fibo correct
            if data['High'].iloc[-1] <= retracement_levels[3] and data['High'].iloc[-2] <= retracement_levels[3]: # le high de la dernière bougie et de l'avant dernoère bougie doivent être inférieur au 0.79 de fibo
                Fibo_correct = True # retourne fibo correct
            else:
                Fibo_correct = False # retourne fibo faux 
        else:
            retracement_levels = [
                data['Low'].iloc[last_low] + level * (data['High'].iloc[last_high] - data['Low'].iloc[last_low]) for level in fib_levels #calcul niveau de retracement
            ]
            Fibo_correct = False # retourne fibo faux
            
            
    else: # Si pas bearish donc bullish
        if data.index[last_low] < data.index[last_high]: # le dernier low doit être placé avant le dernier high 
            retracement_levels = [
                data['High'].iloc[last_high] - level * (data['High'].iloc[last_high] - data['Low'].iloc[last_low]) for level in fib_levels # calcul niveau de retracement 
            ]
            Fibo_correct = True # retourne fibo correcte
            if data['Low'].iloc[-1] >= retracement_levels[3] and data['Low'].iloc[-2] >= retracement_levels[3]:# le low de la dernière et de l'avant dernière bougie doivent être supérieur au 0.79 de fibo
                Fibo_correct = True # retourne fibo correct
            else:
                Fibo_correct = False # retourne fibo faux 
        else:
            retracement_levels = [
                data['High'].iloc[last_high] - level * (data['High'].iloc[last_high] - data['Low'].iloc[last_low]) for level in fib_levels # calcul niveau de retracement 
            ]
            Fibo_correct = False # retourne fibo faux 
            
    max_bougie = max(data['High'])
    min_bougie = min(data['Low'])
    if trend == 'Bullish':
        dimension_minimum = (retracement_levels[0]-retracement_levels[4]) / (max_bougie-min_bougie)
    if trend == 'Bearish':
        dimension_minimum = (retracement_levels[4]-retracement_levels[0]) / (max_bougie-min_bougie)

    if dimension_minimum >= 0.25 and Fibo_correct == True:
        Fibo_correct = False


    # Dessine le graphique
    plt.figure(figsize=(10, 6)) #rapport du graphique
    plt.plot(data['Close'], label='Close', marker='o') #dessine close bougie en rond
    plt.scatter(data.index[major_highs], data['High'].iloc[major_highs], color='red', label='Major Highs') #dessine les majors highs 
    plt.scatter(data.index[major_lows], data['Low'].iloc[major_lows], color='green', label='Major Lows') #dessine les majors lows 
    plt.scatter(data.index[last_low], data['Close'].iloc[last_low], color='orange', marker='o', label='Last Major Low') #dessine les last majors highs 
    plt.scatter(data.index[last_high], data['Close'].iloc[last_high], color='green', marker='o', label='Last Major High') #dessine les lasts majors lows 
    # Plot the chart
    plt.plot(data.index, data['Close'], label='Close Price') #dessine sur graphique 
    
    # Color the candles every 'color_period' candles
    for a in range(0, len(data), color_period):
        color = 'green' if trend == 'Bullish' else 'red' #si bullish alors vert sinon rouge
        plt.axvspan(data.index[a], data.index[a + color_period - 1], alpha=0.1, color=color) #colorie le graphique en  fonction de la tendance

    # Plot ZigZag lines
    plt.vlines(data.index[major_highs], ymin=data['Low'].min(), ymax=data['High'].max(), color='red', linestyle='--', label='ZigZag Highs') # dessine une ligne pointillée en rouge sur les majors highs 
    plt.vlines(data.index[major_lows], ymin=data['Low'].min(), ymax=data['High'].max(), color='green', linestyle='--', label='ZigZag Lows') # dessine une ligne pointillée en vert sur les majors lows 

    # Plot Fibonacci retracement levels
    for i, level in enumerate(retracement_levels):
        plt.hlines(level, xmin=data.index.min(), xmax=data.index.max(), linestyle='--', color=f'C{i+1}', alpha=0.7, linewidth=2, label=f'Fib - {level:.2f}') # dessine le fibo

    # Annotate major highs and lows
    plt.annotate(f'Major Low {last_low}', (data.index[last_low], data['Close'].iloc[last_low]),
                 xytext=(-50, 30), textcoords='offset points',
                 arrowprops=dict(facecolor='black', arrowstyle='wedge,tail_width=0.7', alpha=0.5)) # montre last low sur le graphique

    plt.annotate(f'Major High {last_high}', (data.index[last_high], data['Close'].iloc[last_high]),
                 xytext=(-50, -30), textcoords='offset points',
                 arrowprops=dict(facecolor='black', arrowstyle='wedge,tail_width=0.7', alpha=0.5)) # montre last high sur le graphique
    
    
    plt.legend() #dessine une legende sur le graphique 
    plt.ylim(min(data['Low'].iloc[0:-1]), max(data['High'].iloc[0:-1])) #dezzom en fonction du max et du low des 100 bougies 
    # Save the chart if save_path is provided
    if save_path:
        plt.savefig(save_path)
        plt.close()
    else :
        # Show the chart
        plt.show()
        plt.close()
    
    print(retracement_levels) # indique les retracements fibo 
    print(f"Trend : {trend}") # indique la trend 
    # Return retracement levels
    return retracement_levels, Fibo_correct, dimension_minimum, Fibo_reverese # retourne retracement fibo correct 

data = get_binance_candlestick_data(symbol, limit=100) # extrait les données de binance des 100 dernières bougies 
major_highs, major_lows, last_low, last_high = identify_major_highs_lows(data) # retourne la liste des lows et des highs ainsi que le last major high et low

# Obtenez les indices des derniers major low et high

last_low = major_lows[-1] if major_lows else None 
last_high = major_highs[-1] if major_highs else None
data['Short_MA'] = data['Close'].rolling(window=short_window, min_periods=1).mean()
data['Long_MA'] = data['Close'].rolling(window=long_window, min_periods=1).mean()
    
data['Short_EMA'] = data['Close'].ewm(span=short_window, adjust=False).mean()
data['Long_EMA'] = data['Close'].ewm(span=long_window, adjust=False).mean()
data['MACD'] = data['Short_EMA'] - data['Long_EMA']

# Add a column to indicate the trend (bullish or bearish) based on MACD
data['Trend_MACD'] = 'None'
data.loc[data['MACD'] > 0, 'Trend_MACD'] = 'Bullish' # si data MACD supérieur à 0 alors 'trend MACD'= bullish 
data.loc[data['MACD'] < 0, 'Trend_MACD'] = 'Bearish' # si data MACD inférieur à 0 alors 'trend MACD'= bearish

first_trend = data['Trend_MACD'].iloc[-1] #first trend prend trend MACD
trend= first_trend #trend prend first trend
# Tracez le graphique avec les retracements de Fibonacci et ZigZag
retracement_levels, Fibo_correct, dimension_minimum,Fibo_reverse = plot_fibonacci_and_zigzag(data,first_trend,trend, major_highs, major_lows, last_low, last_high, save_path="fibonacci_and_zigzag_chart.png")

level_price0= retracement_levels[0]
level_price05= retracement_levels[1]
level_price062= retracement_levels[2]
level_price079= retracement_levels[3]
level_price1= retracement_levels[4]


initial_capital = 1000 # initial capital est égal 1000 moulas 
distance_SL=0 # set la distance SL
gain_counter = 0 # set le gain
trade_counter = 0 # set le nombre de trade pris durant la session 
lose_counter = 0 # set le nombre perdue durant la session 
capital = initial_capital # capital prend la valeur de initial capital 
same_retracement = None  # set la variable 
lose_streak = 0
win_streak = 0


print("start") 


while capital < initial_capital*10 : # si le capital est inférieur au inital capital*10 alors ne pas sortir de la boucle 
        print("start in loop")
        data = get_binance_candlestick_data(symbol, limit=100) # prend data des 100 dernières bougies sur Binance 
        # Identifier les niveaux de retracement
        major_highs, major_lows, last_low, last_high = identify_major_highs_lows(data) # retourne la liste des lows et des highs ainsi que le last major high et low
        
        # Plot Fibonacci retracement levels and save the chart
        
        chart_save_path = f"C:/Users/Dytoc/Desktop/Goumbler/fibonacci_chart.png"
        plot_fibonacci_and_zigzag(data,first_trend,trend, major_highs, major_lows, last_low, last_high, save_path=chart_save_path) # tracer le fibo 

        retracement_levels,Fibo_correct, dimension_minimum,Fibo_reverse= plot_fibonacci_and_zigzag(data,first_trend,trend, major_highs, major_lows, last_low, last_high, save_path="fibonacci_and_zigzag_chart.png")

        level_price0= retracement_levels[0]
        level_price05= retracement_levels[1]
        level_price062= retracement_levels[2]
        level_price079= retracement_levels[3]
        level_price1= retracement_levels[4]


        if Fibo_correct == False: # si le fibo tracé est considéré comme incorrect attends une minute et rerentre dans la boucle 

            print(f"Fibo correct : ? : {Fibo_correct}")
            

        if Fibo_correct == True: # si le fibo tracé est considéré comme correcte entrer dans la boucle 
            
            print(f"Fibo correct : ? : {Fibo_correct}")
            if same_retracement!= retracement_levels: # Ancien fibo doit différent du niveau fibo 

                # Send the chart to Discord
                chart_message = f"Nouveau retracement Fibonacci" # set le message discord 
                send_discord_message_with_image(chart_message, chart_save_path) # envoie message sur discord 'nouveau retracement fibo'
                order_place = f"The Goumbler a placé 1 ordres :\n-  0.62 : {level_price062}$\nLe fibo a été placé pour une tendance : {trend} " # set le message discord 
                send_discord_message(order_place) # envoie message sur discord concernant l'ordre placé et la tendance 


            out = False # Sinon passe pas dans la boucle 
            long_counter=0 # compteur de long 
            short_counter=0 # compteur de short 
                
            while out == False and level_price0!= level_price1: # fibo 0 différent fibo 1 ( fibo pas écrasé )

                same_retracement = retracement_levels # ancien fibo = nouveau fibo 
                data = get_binance_candlestick_data(symbol, limit=100) # prend les datas de Binance 
                # Prends toutes les informations de la dernière bougie 
                current_price = data['Close'].iloc[-1] 
                current_price_low = data['Low'].iloc[-1] 
                current_price_high = data['High'].iloc[-1]


                if (level_price062 >= current_price or level_price062 >= current_price_low) and trend == "Bullish" and long_counter==0: #Le retracement fibo 0.62 doit être supérieur au prix actuel et la trend doit être bullish et SL en dessous du prix actuel
                    
                    if lose_streak >= 1:
                        risque = risque/2
                    elif win_streak  == 1:
                        risque = 0.1
                    elif win_streak > 1:
                        risque = 0.12
                    distance_SL=((level_price062 -  level_price1)/level_price062) # calcul distance SL
                    order_size= (capital*risque)/distance_SL # calcul ordersize 
                    levier062 = order_size/ capital #calcul levier 
                    rr062=(((order_size/level_price062)*level_price0) -(order_size))/(capital*risque) #calcul rr
                    order_type = 'Long' #indique le type du trade 
                    long_counter +=1 # long counter prend valeur 1  
                    order_message = f"The Goumbler a {order_type} au {level_price062}, Quantité: {order_size}, levier : {levier062}"
                    send_discord_message(order_message) #envoie message avec toutes les infos concernat le trade qui vient d'être pris 
                    # Placer l'ordre en fonction de la tendance et du niveau de retracement

                if (level_price062 <= current_price or level_price062 <= current_price_high) and trend == "Bearish"and short_counter==0: #Le retracement fibo 0.62 doit être inférieur au prix actuel et la trend doit être bearish et SL au dessus du prix actuel
                    if lose_streak >= 1:
                        risque = risque/2
                    elif win_streak  == 1:
                        risque = 0.1
                    elif win_streak > 1:
                        risque = 0.12
                    # Calculer la distance SL et point d'entrée
                    distance_SL=(-(level_price062 -  level_price1)/level_price062)  # calcul distance SL
                    order_size= (capital*risque)/distance_SL # calcul ordersize 
                    levier062 = order_size/ capital #calcul levier 
                    rr062=-(((order_size/level_price062)*level_price0) -(order_size))/(capital*risque) #calcul rr
                    order_type = 'Short' #indique le type du trade 
                    short_counter +=1 # long counter prend valeur 1
                    # Placer l'ordre en fonction de la tendance et du niveau de retracement
                    order_message = f"The Goumbler a {order_type} au {level_price062}, Quantité: {order_size}, levier : {levier062}"
                    send_discord_message(order_message) #envoie message avec toutes les infos concernat le trade qui vient d'être pris

                if (level_price0 <= current_price or level_price0 <= current_price_high) and trend == "Bullish": # Le TP doit être inférieur ou égal au prix actuel en trend bullish 

                    mise = capital # stocker la valeur du capital 

                    if long_counter == 1: # si il a pris un ordre
                        capital += ((order_size/level_price062)*level_price0) -(order_size) #calcul nouveau capital après TP 
                        rr=rr062 # calcul rr du trade   
                        gain = rr*10 # calcul gain 
                        win_streak += 1
                        lose_streak = 0

                    if long_counter== 0: # si il a pas pris d'ordre 
                        order_paspris = f"Ordres pas pris recherche d'un nouveau fibo" 
                        send_discord_message(order_paspris) # envoie message sur discord ' recherche d'un niveau fibo'
                        last_low_break = last_low
                        last_high_break = last_high
                        while last_low_break == last_low and last_high_break == last_high : # Boucle qui fait que ça recalcul les retracements jusqu'à trouver un nouveau fibo différent du précédent
                            time.sleep(60)
                            data = get_binance_candlestick_data(symbol, limit=100) # prends data de Binance 
                            # Identifier les niveaux de retracement
                            major_highs, major_lows, last_low, last_high, = identify_major_highs_lows(data) #recalcul un nouveau retracement fibo 

                        break 

                    order_type = 'Take profit' 
                    order_message = f"{order_type}, Bravo mon toutou tu es sortie à\nPrix : {level_price0}\nRR: {rr}\nGain :  {gain}%\nQuantité : {mise}\nNouveau capital : {capital}"
                    send_discord_message(order_message, color="vert") # envoie message de win du trade 
                    gain_counter += 1 #mets à jour le nombre de win durant la session 
                    trade_counter +=1 #mets à jour le nombre de trade pris durant la session 
                    if gain_counter/ trade_counter >= 0.3: # si + de 30% winrate colorier le message en bleue 
                        gain_perte_message = f"{symbol}\n{interval} \nTrade gagnés : {gain_counter} \nTrade perdu : {lose_counter} \nWinrate : {gain_counter/ trade_counter*100}% "
                        send_discord_message_gain_perte(gain_perte_message, color="vert")
                    elif gain_counter/ trade_counter < 0.3: # si - de 30% winrate colorier le message en rouge
                        gain_perte_message = f"{symbol}\n{interval} \nTrade gagnés : {gain_counter} \nTrade perdu : {lose_counter} \nWinrate : {gain_counter/ trade_counter*100}% "
                        send_discord_message_gain_perte(gain_perte_message, color="rouge")

                    last_low_break = last_low
                    last_high_break = last_high
                    while last_low_break == last_low and last_high_break == last_high: # Boucle qui fait que ça recalcul les retracements jusqu'à trouver un nouveau fibo différent du précédent
                            time.sleep(60)
                            data = get_binance_candlestick_data(symbol, limit=100) # prend données de Binance 
                            # Identifier les niveaux de retracement
                            major_highs, major_lows, last_low, last_high, = identify_major_highs_lows(data) # recalcul fibo 

                    break 


                    # Placer l'ordre en fonction de la tendance et du niveau de retracement
                if (level_price0 >= current_price or level_price0 >= current_price_low) and trend == "Bearish":
                    mise = capital
                    # Récupérer le prix du niveau de retracement
                    if short_counter == 1:
                        capital += -(((order_size/level_price062)*level_price0) -(order_size))
                        rr=rr062
                        gain = rr*10
                        win_streak += 1
                        lose_streak = 0
                    if short_counter == 0:
                        order_paspris = f"Ordres pas pris recherche d'un nouveau fibo"
                        send_discord_message(order_paspris)
                        last_low_break = last_low
                        last_high_break = last_high

                        while last_low_break == last_low and last_high_break == last_high: # Boucle qui fait que ça recalcul les retracements jusqu'à trouver un nouveau fibo différent du précédent
                            time.sleep(60)
                            data = get_binance_candlestick_data(symbol, limit=100)
                            # Identifier les niveaux de retracement
                            major_highs, major_lows, last_low, last_high, = identify_major_highs_lows(data)

                        break      

                    order_type = 'Take Profit'
                    # Placer l'ordre en fonction de la tendance et du niveau de retracement Bravo mon toutou tu es sortie à: prix soit un rr de: rr et gain = gain + 1
                    order_message = f"{order_type}, Bravo mon toutou tu es sortie à\nPrix : {level_price0}\nRR: {rr}\nGain :  {-gain}%\nQuantité : {mise}\nNouveau capital : {capital}"
                    send_discord_message(order_message, color="vert")
                    gain_counter += 1
                    trade_counter +=1


                    if gain_counter/ trade_counter >= 0.3:
                        gain_perte_message = f"{symbol}\n{interval} \nTrade gagnés : {gain_counter} \nTrade perdu : {lose_counter} \nWinrate : {gain_counter/ trade_counter*100}% "
                        send_discord_message_gain_perte(gain_perte_message, color="vert")
                    elif gain_counter/ trade_counter < 0.3:
                        gain_perte_message = f"{symbol}\n{interval} \nTrade gagnés : {gain_counter} \nTrade perdu : {lose_counter} \nWinrate : {gain_counter/ trade_counter*100}% "
                        send_discord_message_gain_perte(gain_perte_message, color="rouge")
                    last_low_break = last_low
                    last_high_break = last_high

                    while last_low_break == last_low and last_high_break == last_high:  # Boucle qui fait que ça recalcul les retracements jusqu'à trouver un nouveau fibo différent du précédent
                            time.sleep(60)
                            data = get_binance_candlestick_data(symbol, limit=100)
                            # Identifier les niveaux de retracement
                            major_highs, major_lows, last_low, last_high,  = identify_major_highs_lows(data)

                    out = True
                    break

                if (level_price1 >= current_price or level_price1 >= current_price_low) and trend == "Bullish":
                    mise = capital*risque

                    if long_counter == 1:
                        capital = capital - capital*risque
                        win_streak = 0
                        lose_streak += 1
                    if long_counter == 0:
                        order_paspris = f"Ordres pas pris recherche d'un nouveau fibo"
                        send_discord_message(order_paspris)
                        last_low_break = last_low
                        last_high_break = last_high

                        while last_low_break == last_low and last_high_break == last_high: # Boucle qui fait que ça recalcul les retracements jusqu'à trouver un nouveau fibo différent du précédent
                            time.sleep(60)
                            data = get_binance_candlestick_data(symbol, limit=100)
                            # Identifier les niveaux de retracement
                            major_highs, major_lows, last_low, last_high, = identify_major_highs_lows(data)

                        break

                    order_type = 'Liquidation'
                    # Placer l'ordre en fonction de la tendance et du niveau de retracement
                    order_message = f"{order_type} gg ff15 gros noob liquidé à :\n- Prix: {level_price1}\n- Perte : {mise}\n- Nouveau captial : {capital}"
                    send_discord_message(order_message, color="rouge")
                    lose_counter += 1
                    trend = 'Bearish'
                    trade_counter += 1
                    if gain_counter/ trade_counter >= 0.3:
                        gain_perte_message = f"{symbol}\n{interval} \nTrade gagnés : {gain_counter} \nTrade perdu : {lose_counter} \nWinrate : {gain_counter/ trade_counter*100}% "
                        send_discord_message_gain_perte(gain_perte_message, color="vert")
                    elif gain_counter/ trade_counter < 0.3:
                        gain_perte_message = f"{symbol}\n{interval} \nTrade gagnés : {gain_counter} \nTrade perdu : {lose_counter} \nWinrate : {gain_counter/ trade_counter*100}% "
                        send_discord_message_gain_perte(gain_perte_message, color="rouge")


                    last_low_break = last_low
                    last_high_break = last_high

                    while last_low_break == last_low and last_high_break == last_high:  # Boucle qui fait que ça recalcul les retracements jusqu'à trouver un nouveau fibo différent du précédent
                            time.sleep(60)
                            data = get_binance_candlestick_data(symbol, limit=100)
                            # Identifier les niveaux de retracement
                            major_highs, major_lows, last_low, last_high,  = identify_major_highs_lows(data)

                    out = True
                    break


                if (level_price1 <= current_price or level_price1 <= current_price_high) and trend == "Bearish":
                    mise = capital*risque
                    # Récupérer le prix du niveau de retracement
                    if short_counter == 1:
                        capital = capital - capital*risque
                        win_streak = 0
                        lose_streak += 1
                    if short_counter == 0:
                        order_paspris = f"Ordres pas pris recherche d'un nouveau fibo"

                        last_low_break = last_low
                        last_high_break = last_high
                        
                        send_discord_message(order_paspris)
                        while last_low_break == last_low and last_high_break == last_high:  # Boucle qui fait que ça recalcul les retracements jusqu'à trouver un nouveau fibo différent du précédent
                            time.sleep(60)
                            data = get_binance_candlestick_data(symbol, limit=100)
                            # Identifier les niveaux de retracement
                            major_highs, major_lows, last_low, last_high,  = identify_major_highs_lows(data)

                        break

                    order_type = 'Liquidation'
                    # Placer l'ordre en fonction de la tendance et du niveau de retracement
                    order_message = f"{order_type} gg ff15 gros noob liquidé à :\n- Prix: {level_price1}\n- Perte : {mise}\n- Nouveau captial : {capital}"
                    send_discord_message(order_message, color="rouge")
                    lose_counter += 1
                    trend = 'Bullish'
                    trade_counter +=1
                    if gain_counter/ trade_counter >= 0.3:
                        gain_perte_message = f"{symbol}\n{interval} \nTrade gagnés : {gain_counter} \nTrade perdu : {lose_counter} \nWinrate : {gain_counter/ trade_counter*100}% "
                        send_discord_message_gain_perte(gain_perte_message, color="vert")
                    elif gain_counter/ trade_counter < 0.3:
                        gain_perte_message = f"{symbol}\n{interval} \nTrade gagnés : {gain_counter} \nTrade perdu : {lose_counter} \nWinrate : {gain_counter/ trade_counter*100}% "
                        send_discord_message_gain_perte(gain_perte_message, color="rouge")
                    last_low_break = last_low
                    last_high_break = last_high
                    while last_low_break == last_low and last_high_break == last_high:  # Boucle qui fait que ça recalcul les retracements jusqu'à trouver un nouveau fibo différent du précédent
                            time.sleep(60)
                            data = get_binance_candlestick_data(symbol, limit=100)
                            # Identifier les niveaux de retracement
                            major_highs, major_lows, last_low, last_high,  = identify_major_highs_lows(data)

                    out = True
                    break
                    
                time.sleep(60)
            schedule.run_pending()
        time.sleep(60) 
        schedule.run_pending()