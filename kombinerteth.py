import pandas as pd
import matplotlib.pyplot as plt
from binance.client import Client

# Sett opp API-nøklene
api_key = 'din_api_nøkkel'
api_secret = 'din_api_secret'
client = Client(api_key, api_secret)

# Funksjon for å hente aktuell Open Interest
def get_open_interest(symbol):
    try:
        open_interest = client.futures_open_interest(symbol=symbol)
        return float(open_interest['openInterest'])
    except Exception as e:
        print(f"Feil ved henting av Open Interest: {e}")
        return None

# Funksjon for å hente historisk Open Interest med paginering
def get_historical_oi(symbol, interval='1h', total_limit=500):
    try:
        all_data = []
        end_time = None
        remaining_records = total_limit

        while remaining_records > 0:
            limit = min(500, remaining_records)

            # Hent historisk Open Interest-data
            oi_data = client.futures_open_interest_hist(symbol=symbol, period=interval, limit=limit, endTime=end_time)
            
            if not oi_data:
                print("Ingen flere data tilgjengelig fra API.")
                break  # Ingen flere data

            for data in oi_data:
                all_data.append({
                    'timestamp': pd.to_datetime(data['timestamp'], unit='ms'),
                    'open_interest': float(data.get('sumOpenInterest', 0)),  # Sikkerhetskopi hvis nøkkelen mangler
                    'notional_value': float(data.get('sumOpenInterestValue', 0))  # Sikkerhetskopi hvis nøkkelen mangler
                })

            # Oppdater slutt-tidspunkt for neste batch
            end_time = oi_data[-1]['timestamp'] if oi_data else None
            remaining_records -= len(oi_data)

        if not all_data:  # Sjekk om vi har data
            print("Ingen data hentet for historisk Open Interest.")
            return pd.DataFrame()

        df_historical_oi = pd.DataFrame(all_data)
        df_historical_oi.set_index('timestamp', inplace=True)
        return df_historical_oi
    except Exception as e:
        print(f"Feil ved henting av historisk OI-data: {e}")
        return pd.DataFrame()

# Funksjon for å hente pris og volumdata
def get_price_volume(symbol, interval='1h', limit=1000):
    try:
        price_data = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
        price_volume_data = []
        for data in price_data:
            price_volume_data.append({
                'timestamp': pd.to_datetime(data[0], unit='ms'),
                'close': float(data[4]),  # Close pris
                'volume': float(data[5]),  # Volum
            })
        df_price_volume = pd.DataFrame(price_volume_data)
        df_price_volume.set_index('timestamp', inplace=True)
        return df_price_volume
    except Exception as e:
        print(f"Feil ved henting av pris og volumdata: {e}")
        return pd.DataFrame()

# Funksjon for å hente funding rate data
def get_funding_rate(symbol, interval='8h', limit=1000):
    try:
        funding_data = client.futures_funding_rate(symbol=symbol, interval=interval, limit=limit)
        funding_rate_data = []
        for rate in funding_data:
            funding_rate_data.append({
                'timestamp': pd.to_datetime(rate['fundingTime'], unit='ms'),
                'fundingRate': float(rate['fundingRate']),
            })
        df_funding = pd.DataFrame(funding_rate_data)
        df_funding.set_index('timestamp', inplace=True)
        return df_funding
    except Exception as e:
        print(f"Feil ved henting av funding rate data: {e}")
        return pd.DataFrame()

# Funksjon for å beregne limitene basert på valgt intervall
def calculate_limits(interval, funding_limit=1000, oi_limit=500, price_volume_limit=1000):
    # Sett limitene basert på intervallet
    if interval in ['1h', '2h', '4h']:
        # Beregn antall datapunkter avhengig av intervallet
        limit_oi = min(oi_limit, price_volume_limit)
        limit_price_volume = min(price_volume_limit, funding_limit)
    elif interval == '8h':
        limit_oi = oi_limit
        limit_price_volume = price_volume_limit
    else:
        limit_oi = oi_limit
        limit_price_volume = price_volume_limit
    
    return limit_oi, limit_price_volume

# Funksjon for å kombinere pris, volum, funding rate og Open Interest
def get_combined_data(symbol, interval='1h', funding_limit=1000, total_limit_oi=500, price_volume_limit=1000):
    # Beregn limitene for de forskjellige datasettene
    limit_oi, limit_price_volume = calculate_limits(interval, funding_limit, total_limit_oi, price_volume_limit)

    # Hent pris og volumdata
    df_price_volume = get_price_volume(symbol, interval, limit_price_volume)
    
    # Hent funding rate data
    df_funding = get_funding_rate(symbol, interval, funding_limit)

    # Hent historisk Open Interest
    df_oi = get_historical_oi(symbol, interval=interval, total_limit=limit_oi)

    # Kombiner dataene ved å bruke en indre sammenføyning på 'timestamp'
    combined_data = df_price_volume.join(df_funding, how='inner').join(df_oi, how='inner')
       
    return combined_data

# Funksjon for å visualisere dataene
def plot_data(df_combined, symbol):
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(12, 12), sharex=True)

    # Graf for Pris
    ax1.plot(df_combined.index, df_combined['close'], color='blue', label='Pris (Close)')
    ax1.set_ylabel('Pris (Close)', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    ax1.legend(loc='upper left')

    # Graf for Volum
    ax2.bar(df_combined.index, df_combined['volume'], color='orange', alpha=0.3, label='Volum')
    ax2.set_ylabel('Volum', color='orange')
    ax2.tick_params(axis='y', labelcolor='orange')
    ax2.legend(loc='upper left')

    # Graf for Funding Rate
    ax3.plot(df_combined.index, df_combined['fundingRate'], color='green', label='Funding Rate')
    ax3.set_ylabel('Funding Rate', color='green')
    ax3.tick_params(axis='y', labelcolor='green')
    ax3.legend(loc='upper left')

    # Graf for Open Interest
    ax4.plot(df_combined.index, df_combined['open_interest'], color='purple', label='Open Interest')
    ax4.set_ylabel('Open Interest', color='purple')
    ax4.tick_params(axis='y', labelcolor='purple')
    ax4.legend(loc='upper left')

    # Legg til tittel for hele figuren
    plt.suptitle(f'Pris, Volum, Funding Rate og Open Interest for {symbol}', fontsize=16)
    
    # Legg til gitter
    plt.grid(True)
    
    # Vis diagrammet
    plt.tight_layout()
    plt.show()

# Hovedprogram
symbol = 'ETHUSDT'

# Sett intervall og limits her
interval = '1h'  # Eksempel: kan endres til '1h', '2h', '4h', '8h' etc.
funding_limit = 1000  # Funding rate limit er alltid 1000

# Beregn dynamiske limits for pris/volum og OI basert på intervallet
total_limit_oi, price_volume_limit = calculate_limits(interval, funding_limit)

# Hent de kombinerte dataene
combined_data = get_combined_data(symbol, interval, funding_limit, total_limit_oi, price_volume_limit)

# Hvis kombinerte data er hentet, visualiser
if not combined_data.empty:
    plot_data(combined_data, symbol)
else:
    print("Ingen data ble hentet.")
