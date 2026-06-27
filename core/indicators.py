import pandas as pd


def calcular_indicadores(df, mms_periodos, rsi_ativo, stoch_ativo):
    if df is None or len(df) < 20:
        return df
    df = df.ffill()
    if mms_periodos:
        for p in mms_periodos:
            df[f"MMS_{p}"] = df["Close"].rolling(window=p).mean()
            # O critério agora é baseado em ESTADO (acima/abaixo) em vez de CRUZAMENTO
            df[f"MMS_{p}_Above"] = df["Close"] > df[f"MMS_{p}"]
            df[f"MMS_{p}_Below"] = df["Close"] < df[f"MMS_{p}"]
    if rsi_ativo:
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1 / 14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / 14, adjust=False).mean()
        loss = loss.replace(0, 1e-9)
        rs = gain / loss
        df["RSI_14"] = 100 - (100 / (1 + rs))
        df["RSI_MA"] = df["RSI_14"].rolling(window=14).mean()
    if stoch_ativo:
        low_min = df["Low"].rolling(window=14).min()
        high_max = df["High"].rolling(window=14).max()
        denom = (high_max - low_min).replace(0, 1e-9)
        df["STOCH_K_raw"] = 100 * ((df["Close"] - low_min) / denom)
        df["STOCH_K"] = df["STOCH_K_raw"].rolling(window=3).mean()
        df["STOCH_D"] = df["STOCH_K"].rolling(window=3).mean()
    return df


def verificar_confluencia(df_row, mms_periodos, rsi_ativo, stoch_ativo, close_price):
    sinal_mms, sinal_rsi, sinal_stoch = 0, 0, 0
    if mms_periodos:
        all_crossed_up = all_crossed_down = True
        for p in mms_periodos:
            is_above = df_row.get(f"MMS_{p}_Above", False)
            is_below = df_row.get(f"MMS_{p}_Below", False)
            if not is_above:
                all_crossed_up = False
            if not is_below:
                all_crossed_down = False

        if all_crossed_up:
            sinal_mms = 1
        elif all_crossed_down:
            sinal_mms = -1

    if rsi_ativo:
        rsi, rsi_ma = df_row.get("RSI_14", 50), df_row.get("RSI_MA", 50)
        if pd.notna(rsi) and pd.notna(rsi_ma):
            if rsi > rsi_ma:
                sinal_rsi = 1
            elif rsi < rsi_ma:
                sinal_rsi = -1
    if stoch_ativo:
        stoch_k, stoch_d = df_row.get("STOCH_K", 50), df_row.get("STOCH_D", 50)
        if pd.notna(stoch_k) and pd.notna(stoch_d):
            if stoch_k > stoch_d:
                sinal_stoch = 1
            elif stoch_k < stoch_d:
                sinal_stoch = -1
    return sinal_mms, sinal_rsi, sinal_stoch
